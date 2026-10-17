// Large cloud bundles are fetched as private, authenticated parts. Each server
// response stays below the platform limit; the admin receives one ordinary ZIP.
export async function downloadResponse(response, fallbackName, save, progress=()=>{}) {
  if (!response.ok) {
    const result=await response.json().catch(()=>({}));
    throw new Error(result.error||'Chưa tải được file. Thử lại sau.');
  }
  const contentType=response.headers.get('Content-Type')||'application/octet-stream';
  if (!contentType.includes('application/json')) {
    const match=response.headers.get('Content-Disposition')?.match(/filename\*=UTF-8''([^;]+)/i);
    const filename=match?decodeURIComponent(match[1]):fallbackName;
    save(await response.arrayBuffer(),filename,contentType);
    return filename;
  }
  const manifest=await response.json();
  if (manifest.format!=='xuanhoa-download-v1'||!Array.isArray(manifest.items)||!manifest.items.length||manifest.items.length>1000)
    throw new Error('Danh sách file tải chưa hợp lệ.');
  const {default:JSZip}=await import('jszip');
  const archive=new JSZip();
  const names=new Set();
  for (const [index,item] of manifest.items.entries()) {
    if (typeof item.filename!=='string'||item.filename.includes('\\')||item.filename.startsWith('/')||
        item.filename.split('/').some(part=>part==='..'||part==='.')||names.has(item.filename))
      throw new Error('Tên file trong gói tải không hợp lệ.');
    if (typeof item.url!=='string'||!item.url.startsWith('/api/')||new URL(item.url,location.origin).origin!==location.origin)
      throw new Error('Đường dẫn tải file không hợp lệ.');
    names.add(item.filename);
    progress(`Đang tải ${index+1} / ${manifest.items.length} file…`);
    const part=await fetch(item.url,{cache:'no-store',credentials:'same-origin'});
    if (!part.ok) {
      const error=await part.json().catch(()=>({}));
      throw new Error(error.error||`Chưa tải được file ${index+1}. Bấm tải lại để tạo đủ gói.`);
    }
    archive.file(item.filename,await part.arrayBuffer());
  }
  if (manifest.readme)archive.file('manifest.json',JSON.stringify(manifest.readme,null,2));
  progress('Đang ghép gói ZIP…');
  const data=await archive.generateAsync({type:'blob',compression:'STORE'});
  const filename=manifest.filename||fallbackName;
  save(data,filename,'application/zip');
  return filename;
}
