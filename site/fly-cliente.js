// Cliente do FLY, compartilhado pela pagina publica e pela /dev:
//  1. decodeDV: indices dos neuronios que dispararam, em delta-varint (ordenados, diferenca em varint de 7 bits)
//  2. Corpo3D: a mosca desenhada no navegador em three.js a partir do modelo exportado (fly-model.json/bin) e dos
//     quadros de pose (qpos inteiro + camera) que corpo/corpo.py manda 30x por segundo; cinematica direta igual
//     ao mj_kinematics do MuJoCo (pais antes dos filhos, juntas na ordem, dobradica em torno do proprio ponto).
window.decodeDV=function(u8){
  const out=new Uint32Array(u8.length); let n=0, acc=0, i=0;
  while(i<u8.length){ let v=0, s=0, b; do{ b=u8[i++]; v|=(b&0x7F)<<s; s+=7; }while((b&0x80) && i<u8.length); acc+=v; out[n++]=acc; }
  return out.subarray(0,n);
};

window.Corpo3D=(function(){
  const ATRASO_MS=50;                 // renderiza um pouco atras do ultimo quadro para interpolar entre dois
  const S={pronto:false, ren:null, scene:null, cam:null, mosca:null, espelho:null, corpos:[], objs:[], objsE:[],
           juntas:[], matriz:[], q:[null,null], t:[0,0], cams:[null,null], nq:0, fovy:45, canvas:null, box:null,
           ultimo:0, qi:null, erro:null};
  const M=new THREE.Matrix4(), M2=new THREE.Matrix4(), M3=new THREE.Matrix4(), Q=new THREE.Quaternion();
  const V=new THREE.Vector3(), V2=new THREE.Vector3(), UM=new THREE.Vector3(1,1,1);

  function TR(pos, quat, out){ return out.compose(V.set(pos[0],pos[1],pos[2]), Q.set(quat[1],quat[2],quat[3],quat[0]), UM); }

  async function init(canvas){
    S.canvas=canvas; S.box=canvas.parentElement;
    try{
      const [j,bin]=await Promise.all([fetch('/static/fly-model.json').then(r=>r.json()), fetch('/static/fly-model.bin').then(r=>r.arrayBuffer())]);
      montar(j,bin); S.pronto=true; requestAnimationFrame(loop);
    }catch(e){ S.erro=e; console.error('Corpo3D', e); }
  }

  function montar(j,bin){
    S.nq=j.nq; S.fovy=(j.cam&&j.cam.fovy)||45;
    S.ren=new THREE.WebGLRenderer({canvas:S.canvas, antialias:true, alpha:false, powerPreference:'high-performance'});
    S.ren.setClearColor(0x000000,1); S.ren.outputColorSpace=THREE.SRGBColorSpace;
    S.scene=new THREE.Scene(); S.scene.background=new THREE.Color(0x000000);
    S.cam=new THREE.PerspectiveCamera(S.fovy, 2, 0.3, 500); S.cam.up.set(0,0,1);
    // luzes: o palco do MuJoCo tem headlight + um sol de cima um pouco de lado
    S.scene.add(new THREE.HemisphereLight(0xffffff, 0x14141a, 0.85));
    const sol=new THREE.DirectionalLight(0xfff4e2, 1.5); sol.position.set(-3,-4,10); S.scene.add(sol);
    const contra=new THREE.DirectionalLight(0x9fb8ff, 0.35); contra.position.set(6,3,3); S.scene.add(contra);
    const loader=new THREE.TextureLoader(); const texs={}, mats={}, matsE={};
    for(const [k,m] of Object.entries(j.materiais)){
      let map=null;
      if(m.tex){ map=texs[m.tex]; if(!map){ map=loader.load('/static/fly-tex/'+m.tex+'.png'); map.flipY=false; map.colorSpace=THREE.SRGBColorSpace; map.anisotropy=4; texs[m.tex]=map; } }
      const cor=new THREE.Color(m.rgba[0],m.rgba[1],m.rgba[2]); const a=m.rgba[3];
      mats[k]=new THREE.MeshStandardMaterial({color:cor, map, transparent:a<0.999, opacity:a, roughness:Math.max(0.3,1-0.7*(m.shininess||0.3)), metalness:0.0, side:THREE.DoubleSide});
      // reflexo no chao: copia escura e translucida, espelhada em z
      matsE[k]=new THREE.MeshBasicMaterial({color:cor.clone().multiplyScalar(0.5), map, transparent:true, opacity:0.20*a, side:THREE.DoubleSide, depthWrite:false});
    }
    const geos=j.malhas.map(ml=>{
      const g=new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(bin, ml.off_pos, ml.nv*3),3));
      if(ml.uv) g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(bin, ml.off_uv, ml.nv*2),2));
      g.setIndex(new THREE.BufferAttribute(ml.idx16?new Uint16Array(bin, ml.off_idx, ml.nf*3):new Uint32Array(bin, ml.off_idx, ml.nf*3),1));
      g.computeVertexNormals(); return g;
    });
    S.mosca=new THREE.Group(); S.espelho=new THREE.Group(); S.espelho.scale.set(1,1,-1);
    S.scene.add(S.mosca); S.scene.add(S.espelho);
    S.corpos=j.corpos; S.juntas=j.corpos.map(()=>[]); j.juntas.forEach(jt=>S.juntas[jt.corpo].push(jt));
    S.matriz=j.corpos.map(()=>new THREE.Matrix4());
    S.objs=j.corpos.map(()=>{ const o=new THREE.Object3D(); o.matrixAutoUpdate=false; S.mosca.add(o); return o; });
    S.objsE=j.corpos.map(()=>{ const o=new THREE.Object3D(); o.matrixAutoUpdate=false; S.espelho.add(o); return o; });
    for(const g of j.geoms){
      const mk=new THREE.Mesh(geos[g.malha], mats[g.mat]); mk.matrixAutoUpdate=false; TR(g.pos,g.quat,mk.matrix); mk.renderOrder=2; S.objs[g.corpo].add(mk);
      const me=new THREE.Mesh(geos[g.malha], matsE[g.mat]); me.matrixAutoUpdate=false; me.matrix.copy(mk.matrix); me.renderOrder=0; S.objsE[g.corpo].add(me);
    }
    // chao preto de verdade (sem luz, senao vira uma laje cinza), um pouco translucido para o reflexo aparecer por baixo
    const chao=new THREE.Mesh(new THREE.PlaneGeometry(600,600), new THREE.MeshBasicMaterial({color:0x000000, transparent:true, opacity:0.80, depthWrite:false}));
    chao.renderOrder=1; S.scene.add(chao);
    S.qi=new Float32Array(S.nq);
    redimensionar(); new ResizeObserver(redimensionar).observe(S.box);
  }

  function redimensionar(){
    if(!S.ren) return;
    const r=S.box.getBoundingClientRect(); const w=Math.max(2,r.width), h=Math.max(2,r.height);
    S.ren.setPixelRatio(Math.min(1.5, window.devicePixelRatio||1)); S.ren.setSize(w,h,false);
    S.cam.aspect=w/h; S.cam.updateProjectionMatrix();
  }

  // cinematica direta: corpo = pai * T(pos)R(quat) * juntas(q); a junta livre da raiz vem inteira do qpos
  function aplicar(q){
    for(let b=0;b<S.corpos.length;b++){
      const c=S.corpos[b], jl=S.juntas[b], W=S.matriz[b];
      if(jl.length && jl[0].tipo===0){ const a=jl[0].qadr; W.compose(V.set(q[a],q[a+1],q[a+2]), Q.set(q[a+4],q[a+5],q[a+6],q[a+3]).normalize(), UM); }
      else{
        TR(c.pos,c.quat,W);
        for(const jt of jl){ const a=jt.qadr;
          if(jt.tipo===3){ M.makeTranslation(jt.pos[0],jt.pos[1],jt.pos[2]); M2.makeRotationAxis(V.set(jt.eixo[0],jt.eixo[1],jt.eixo[2]), q[a]); M3.makeTranslation(-jt.pos[0],-jt.pos[1],-jt.pos[2]); W.multiply(M).multiply(M2).multiply(M3); }
          else if(jt.tipo===2){ M.makeTranslation(jt.eixo[0]*q[a],jt.eixo[1]*q[a],jt.eixo[2]*q[a]); W.multiply(M); }
          else if(jt.tipo===1){ M.makeTranslation(jt.pos[0],jt.pos[1],jt.pos[2]); M2.makeRotationFromQuaternion(Q.set(q[a+1],q[a+2],q[a+3],q[a]).normalize()); M3.makeTranslation(-jt.pos[0],-jt.pos[1],-jt.pos[2]); W.multiply(M).multiply(M2).multiply(M3); }
        }
        if(c.pai>=0) W.premultiply(S.matriz[c.pai]);
      }
      S.objs[b].matrix.copy(W); S.objsE[b].matrix.copy(W);
    }
  }

  function quadro(j, bytes){
    const q=new Float32Array(bytes);
    if(!S.pronto || q.length!==S.nq) return;
    S.q[0]=S.q[1]; S.t[0]=S.t[1]; S.cams[0]=S.cams[1];
    S.q[1]=q; S.t[1]=performance.now(); S.cams[1]=j.cam; S.ultimo=S.t[1];
  }

  function loop(){
    requestAnimationFrame(loop);
    if(!S.pronto || !S.q[1] || !S.cams[1]) return;
    if(performance.now()-S.ultimo>8000) return;                // corpo parado: nao gasta a placa
    let q=S.q[1], c=S.cams[1];
    if(S.q[0] && S.cams[0]){
      const dt=Math.max(1, S.t[1]-S.t[0]); const alpha=Math.max(0, Math.min(1, (performance.now()-ATRASO_MS-S.t[0])/dt));
      const q0=S.q[0], q1=S.q[1], qi=S.qi;
      for(let i=0;i<qi.length;i++) qi[i]=q0[i]+(q1[i]-q0[i])*alpha;
      q=qi;
      const c0=S.cams[0], c1=S.cams[1]; let daz=c1[3]-c0[3]; daz=((daz+Math.PI)%(2*Math.PI)+2*Math.PI)%(2*Math.PI)-Math.PI;
      c=[c0[0]+(c1[0]-c0[0])*alpha, c0[1]+(c1[1]-c0[1])*alpha, c0[2]+(c1[2]-c0[2])*alpha, c0[3]+daz*alpha, c1[4], c1[5]];
    }
    aplicar(q);
    const az=c[3], el=c[4], d=c[5];
    S.cam.position.set(c[0]+d*Math.cos(el)*Math.cos(az), c[1]+d*Math.cos(el)*Math.sin(az), c[2]+d*Math.sin(el));
    S.cam.lookAt(c[0],c[1],c[2]);
    S.ren.render(S.scene, S.cam);
  }

  return {init, quadro, estado:S};
})();
