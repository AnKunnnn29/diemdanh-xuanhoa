// Shared external print behavior, compatible with script-src 'self'.
window.renderPrintDocument=html=>{
  const parsed=new DOMParser().parseFromString(html,'text/html');
  // Print templates are assembled by the application with escaped values.
  // Never import executable elements or event attributes from the markup.
  parsed.querySelectorAll('script,iframe,object,embed,base,link,meta').forEach(node=>node.remove());
  parsed.querySelectorAll('*').forEach(node=>{for(const attribute of [...node.attributes])if(attribute.name.startsWith('on'))node.removeAttribute(attribute.name);});
  document.title=parsed.title||'In / Lưu PDF';
  document.head.querySelectorAll('style').forEach(style=>style.remove());
  for(const style of parsed.head.querySelectorAll('style'))document.head.append(document.importNode(style,true));
  document.body.replaceChildren(...[...parsed.body.childNodes].map(node=>document.importNode(node,true)));
  const printButton=document.getElementById('print');
  if(printButton){printButton.addEventListener('click',()=>window.print());printButton.disabled=false;}
};
