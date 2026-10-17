import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
// Build from source. Only the existing web output goes into Vercel's CDN;
// workbook/state exports and environment files are never copied here.
execFileSync(process.execPath,['build.mjs'],{stdio:'inherit'});
const root=path.resolve('dist'),destination=path.resolve('public');
for(const entry of fs.readdirSync(root,{recursive:true,withFileTypes:true})){
  if(entry.isSymbolicLink())throw new Error('Unexpected link in web output.');
  if(entry.isFile()&&/\.(?:xlsm|xlsx|sqlite3?|env|pem|key|csv|zip)$/i.test(entry.name))throw new Error('Private data found in web output.');
}
fs.mkdirSync(destination,{recursive:true});
fs.cpSync(root,destination,{recursive:true});
console.log('Cloud web assets prepared in public/. No deployment performed.');
