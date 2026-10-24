// Navigate a same-origin print page instead of document.write/about:blank.
export async function renderPrintWindow(win,html){
  await new Promise((resolve,reject)=>{
    const started=Date.now();
    const timer=setInterval(()=>{
      if(win.closed||Date.now()-started>15000){clearInterval(timer);reject(new Error('Chưa mở được trang in. Thử lại khi có kết nối.'));return;}
      try{if(win.location.origin===location.origin&&win.location.pathname==='/print.html'&&typeof win.renderPrintDocument==='function'){clearInterval(timer);resolve();}}catch{}
    },50);
  });
  win.renderPrintDocument(html);
}
