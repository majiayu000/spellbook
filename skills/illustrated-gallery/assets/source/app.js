const slides=[
{src:'assets/bloom.webp',alt:'蓝白花卉插画',name:'A BOTANICAL DREAM',focus:0.68},
{src:'assets/tide.webp',alt:'水中的白色锦鲤',name:'BETWEEN THE TIDES',focus:0.72},
{src:'assets/heron.webp',alt:'莲叶之间的白鹭',name:'WINGS OF STILLNESS',focus:0.7},
{src:'assets/moon.webp',alt:'月光下的蓝色森林',name:'UNDER THE IVORY MOON',focus:0.76},
{src:'assets/muse.webp',alt:'花朵之间的女性侧脸',name:'A QUIET IMAGINATION',focus:0.52}];
const hero=document.querySelector('.hero'),scene=document.querySelector('.scene'),pause=document.querySelector('#pause'),bar=document.querySelector('.progress span');
const canvas=document.querySelector('#dissolve'),ctx=canvas.getContext('2d');
const sample=document.createElement('canvas'),sc=sample.getContext('2d',{willReadFrequently:true});
const mobile=matchMedia('(max-width:760px)');
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
let index=0,paused=reduced.matches,busy=false,elapsed=0,last=performance.now();
const images=slides.map(()=>new Image());
function imageFor(n){if(!images[n].getAttribute('src'))images[n].src=slides[n].src;return images[n];}
imageFor(0);if(slides.length>1)imageFor(1);
const selectors=document.querySelectorAll('[data-select]');
selectors.forEach(button=>button.addEventListener('click',()=>go(Number(button.dataset.select))));
function pauseUI(){pause.textContent=paused?'▶':'Ⅱ';pause.setAttribute('aria-label',paused?'播放轮播':'暂停轮播');pause.setAttribute('aria-pressed',String(paused));}
pauseUI();
function pad2(n){return String(n).padStart(2,'0');}
function commit(n){index=n;scene.src=slides[n].src;scene.alt=slides[n].alt;document.querySelector('#counter').textContent=`${pad2(n+1)} / ${pad2(slides.length)}`;document.querySelector('#scene-name').textContent=`${pad2(n+1)} — ${slides[n].name}`;elapsed=0;hero.style.setProperty('--focus',`${slides[n].focus*100}%`);hero.dataset.scene=String(n);selectors.forEach((b,i)=>b.setAttribute('aria-pressed',String(i===n)));if(slides.length>1)imageFor((n+1)%slides.length);}
commit(0);
function sampleImage(im,w,h,n){sample.width=w;sample.height=h;const scale=Math.max(w/im.naturalWidth,h/im.naturalHeight);const iw=im.naturalWidth*scale,ih=im.naturalHeight*scale;sc.drawImage(im,(w-iw)*(mobile.matches?slides[n].focus:.5),(h-ih)/2,iw,ih);return sc.getImageData(0,0,w,h).data;}
async function go(n){if(busy)return;n=(n+slides.length)%slides.length;if(n===index)return;busy=true;try{await Promise.all([imageFor(index).decode(),imageFor(n).decode()]);document.querySelector('#media-error').hidden=true;if(reduced.matches){commit(n);busy=false;return;}const width=hero.clientWidth,height=hero.clientHeight;canvas.width=width;canvas.height=height;const step=10,cols=Math.ceil(width/step),rows=Math.ceil(height/step),old=sampleImage(images[index],cols,rows,index),next=sampleImage(images[n],cols,rows,n),noise=Float32Array.from({length:cols*rows},()=>Math.random());const start=performance.now();let switched=false;ctx.font='10px monospace';ctx.textBaseline='top';function render(now){const p=Math.min(1,(now-start)/1500);if(p>=.5&&!switched){commit(n);switched=true;}ctx.fillStyle='#0b2c33';ctx.fillRect(0,0,width,height);const reveal=Math.max(0,Math.min(1,(p-.28)/.44));for(let y=0;y<rows;y++)for(let x=0;x<cols;x++){const cell=y*cols+x,k=cell*4;const data=noise[cell]<reveal?next:old;const lum=(data[k]*.2126+data[k+1]*.7152+data[k+2]*.0722)/255;ctx.fillStyle=`rgb(${Math.min(255,data[k]*1.3+20)} ${Math.min(255,data[k+1]*1.3+20)} ${Math.min(255,data[k+2]*1.3+20)})`;const chars=' .:;+=*#%@';ctx.fillText(chars[Math.min(9,Math.floor(lum*10))],x*step,y*step);}canvas.style.opacity=String(Math.min(1,p*5,(1-p)*5));if(p<1)requestAnimationFrame(render);else{canvas.style.opacity='0';busy=false;elapsed=0;}}requestAnimationFrame(render);}catch(error){busy=false;paused=true;pauseUI();document.querySelector('#media-error').hidden=false;console.error('Gallery image failed to load',error);}}
document.querySelector('#prev').addEventListener('click',()=>go(index-1));document.querySelector('#next').addEventListener('click',()=>go(index+1));pause.addEventListener('click',()=>{paused=!paused;pauseUI();});
reduced.addEventListener('change',()=>{if(reduced.matches){paused=true;pauseUI();}});
function tick(now){const dt=Math.min(now-last,100);last=now;if(!paused&&!busy&&!document.hidden){elapsed+=dt;if(elapsed>=10000)go(index+1);}bar.style.width=`${Math.min(elapsed/10000*100,100)}%`;requestAnimationFrame(tick);}requestAnimationFrame(tick);
scene.addEventListener('error',()=>{document.querySelector('#media-error').hidden=false;paused=true;pauseUI();});
document.querySelectorAll('[data-slide]').forEach(card=>card.addEventListener('click',()=>{go(Number(card.dataset.slide));hero.scrollIntoView({behavior:reduced.matches?'instant':'smooth'});}));
let touchStart=null;
hero.addEventListener('touchstart',event=>{if(event.touches.length!==1||event.target.closest('button,a')){touchStart=null;return;}const t=event.touches[0];touchStart={x:t.clientX,y:t.clientY};},{passive:true});
hero.addEventListener('touchend',event=>{if(!touchStart)return;const t=event.changedTouches[0],dx=t.clientX-touchStart.x,dy=t.clientY-touchStart.y;touchStart=null;if(Math.abs(dx)>55&&Math.abs(dx)>Math.abs(dy)*1.5)go(index+(dx<0?1:-1));},{passive:true});
hero.addEventListener('touchcancel',()=>touchStart=null,{passive:true});
const dialog=document.querySelector('#contact-dialog');document.querySelector('#contact-open').addEventListener('click',()=>dialog.showModal());dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
document.querySelector('#brief-form').addEventListener('submit',e=>{e.preventDefault();const idea=document.querySelector('#brief').value.trim();if(!idea){document.querySelector('#brief').setCustomValidity('请写下你的想法。');document.querySelector('#brief').reportValidity();return;}const blob=new Blob([`# Blue Hour 创意简报\n\n${idea}\n`],{type:'text/markdown;charset=utf-8'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='blue-hour-brief.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});document.querySelector('#brief').addEventListener('input',e=>e.target.setCustomValidity(''));
