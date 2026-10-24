import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
// Build from source. Only the existing web output goes into Vercel's CDN;
// workbook/state exports and environment files are never copied here.
execFileSync(process.execPath,['build.mjs'],{stdio:'inherit'});
const root=path.resolve('dist'),destination=path.resolve('public');
function inspectOutput(directory){for(const entry of fs.readdirSync(directory,{recursive:true,withFileTypes:true})){
  if(entry.isSymbolicLink())throw new Error('Unexpected link in web output.');
  const publicLicenses=new Set(['nunito-license.txt','newsreader-license.txt','baloo2-license.txt']);
  if(entry.isFile()&&!publicLicenses.has(entry.name)&&(/^\.env/i.test(entry.name)||/\.(?:xlsm|xlsx|sqlite3?|env|pem|key|csv|zip|sql|age|p12|docx|pdf|txt)$/i.test(entry.name)))throw new Error('Private data found in web output.');
}}
inspectOutput(root);
if(fs.existsSync(destination))inspectOutput(destination);
fs.mkdirSync(destination,{recursive:true});
fs.cpSync(root,destination,{recursive:true});
console.log('Cloud web assets prepared in public/. No deployment performed.');
