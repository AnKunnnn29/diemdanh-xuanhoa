// CSS transforms on an SVG <g> can invalidate SVG layout every frame. Keep the
// original vector paths, but animate a tightly bounded HTML box instead. Its
// nested SVG preserves the artwork coordinates and shared gradient references.
export function prepareWelcomeSvgMotion(root){
  if(!Element.prototype.animate)return;
  const svgNS='http://www.w3.org/2000/svg',htmlNS='http://www.w3.org/1999/xhtml';
  // Keep the small dove wings in their original SVG coordinate system. Nested
  // foreignObject transforms are unreliable when the bird scales on mobile.
  const selector='[data-welcome-ambient],[data-welcome-light],[data-welcome-depth]';
  // Read all bounds before replacing nodes; no per-frame geometry work.
  const targets=[...root.querySelectorAll(selector)].filter(node=>node instanceof SVGElement).map(node=>({
    node,bounds:node.getBBox(),origin:getComputedStyle(node).transformOrigin.split(' ').map(parseFloat)
  }));
  for(const {node,bounds,origin} of targets){
    if(!bounds.width||!bounds.height)continue;
    const frame=document.createElementNS(svgNS,'foreignObject');
    for(const key of ['x','y','width','height'])frame.setAttribute(key,bounds[key]);
    frame.classList.add('welcome-motion-frame');
    const box=document.createElementNS(htmlNS,'div');
    for(const attribute of [...node.attributes])if(attribute.name==='class'||attribute.name.startsWith('data-welcome-')){
      box.setAttribute(attribute.name,attribute.value);node.removeAttribute(attribute.name);
    }
    box.classList.add('welcome-svg-motion');
    box.style.transformOrigin=`${origin[0]-bounds.x}px ${origin[1]-bounds.y}px`;
    const svg=document.createElementNS(svgNS,'svg');
    svg.setAttribute('viewBox',`${bounds.x} ${bounds.y} ${bounds.width} ${bounds.height}`);
    svg.classList.add('welcome-motion-viewport');
    node.replaceWith(frame);frame.append(box);box.append(svg);svg.append(node);
  }
}
