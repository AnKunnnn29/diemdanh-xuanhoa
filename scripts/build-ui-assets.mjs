import {build} from 'esbuild';
import {mkdirSync,copyFileSync,readFileSync,writeFileSync} from 'node:fs';
import JSZip from 'jszip';
import path from 'node:path';
import {writeAnimations} from './generate-ui-animations.mjs';

export async function buildUIAssets(root='dist'){
  writeAnimations(path.join(root,'assets/animations'));
  // Unpack the supplied dotLottie archives at build time; keep the existing player.
  const animationDir=path.join(root,'assets/animations');
  for(const [source,name] of [['Loader cat.lottie','loading-cat'],['Cat playing animation.lottie','playing-cat'],['success confetti.lottie','success-confetti']]){
    const archive=await JSZip.loadAsync(readFileSync(new URL('../assets-source/animations/'+encodeURIComponent(source),import.meta.url)));
    const manifest=JSON.parse(await archive.file('manifest.json').async('string'));
    const data=JSON.parse(await archive.file('animations/'+manifest.animations[0].id+'.json').async('string'));
    writeFileSync(path.join(animationDir,name+'.json'),JSON.stringify(data));
    const drawing=name==='success-confetti'
      ? '<circle cx="140" cy="100" r="46" fill="#dcfce7"/><path d="m116 100 16 16 32-34" fill="none" stroke="#166534" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
      : '<path d="M96 87 91 48 121 65Q140 59 159 65L189 48 184 87Q201 137 140 145 79 137 96 87Z" fill="#dcfce7" stroke="#303c4b" stroke-width="4" stroke-linejoin="round"/><path d="M118 99h2m40 0h2m-29 15 7 5 7-5m-42-3-25-5m25 16-25 3m95-14 25-5m-25 16 25 3" fill="none" stroke="#303c4b" stroke-width="4" stroke-linecap="round"/>';
    writeFileSync(path.join(animationDir,name+'.svg'),`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 200">${drawing}</svg>`);
  }
  const vendor=path.join(root,'assets/vendor');mkdirSync(vendor,{recursive:true});
  // The distributed ESM file is not minified despite its filename.
  // Keep this separate from app.js so the renderer loads only when needed.
  await build({entryPoints:['node_modules/lottie-web/build/player/esm/lottie_light.min.js'],bundle:true,minify:true,
    target:'es2020',format:'esm',outfile:path.join(vendor,'lottie-light.min.js')});
  copyFileSync('node_modules/lottie-web/LICENSE.md',path.join(vendor,'LOTTIE-LICENSE.md'));
}
