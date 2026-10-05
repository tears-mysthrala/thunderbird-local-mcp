async function refresh(){try{const result=await browser.runtime.sendMessage({method:'diagnostics'});document.querySelector('#status').textContent=JSON.stringify(result,null,2);}catch{document.querySelector('#status').textContent='El proceso de fondo no responde';}}
document.querySelector('#refresh').addEventListener('click',refresh);
document.querySelector('#reconnect').addEventListener('click',async()=>{await browser.runtime.sendMessage({method:'reconnect'});await refresh();});
refresh();
