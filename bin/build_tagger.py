#!/usr/bin/env python3
"""
build_tagger.py - turn a understudy eval batch into a standalone, keyboard-driven
HTML tagging app. Reusable: point it at any eval dir that has
  eval_drafts.jsonl  (id, recipient, channel, context, claude_draft)
  revised.jsonl      (id, spec_v2_revised)
  eval_truth.jsonl   (id, matt_sent)
  panel-key.json     ({id: {A: source, B: source}})
and it emits a self-contained .html (no network, opens from file://).

Usage:
  python3 build_tagger.py <eval_dir> <out.html> [batch_label]
"""
import json, sys, html, pathlib

eval_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                        "/Users/mattbeane/.claude/skills/wild-voice/corpus/v2")
out_path = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else
                        str(pathlib.Path.home() / "Downloads/voice-tagger.html"))
batch = sys.argv[3] if len(sys.argv) > 3 else "v2"

def load_jsonl(p):
    d = {}
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
            d[o["id"]] = o
        except Exception:
            pass
    return d

drafts = load_jsonl(eval_dir / "eval_drafts.jsonl")
revised = load_jsonl(eval_dir / "revised.jsonl")
truth = load_jsonl(eval_dir / "eval_truth.jsonl")
key = json.load(open(eval_dir / "panel-key.json", encoding="utf-8"))

src_text = {"claude_draft": drafts, "spec_v2_revised": revised, "matt_sent": truth}
src_field = {"claude_draft": "claude_draft", "spec_v2_revised": "spec_v2_revised", "matt_sent": "matt_sent"}

items = []
for i, (pid, ab) in enumerate(key.items(), start=1):
    if pid not in drafts or pid not in revised:
        continue
    def text_for(source):
        store = src_text.get(source, {})
        return (store.get(pid) or {}).get(src_field.get(source, ""), "")
    items.append({
        "item": i,
        "id": pid,
        "recipient": drafts[pid].get("recipient", ""),
        "channel": drafts[pid].get("channel", ""),
        "context": drafts[pid].get("context", ""),
        "A": {"text": text_for(ab["A"]), "source": ab["A"]},
        "B": {"text": text_for(ab["B"]), "source": ab["B"]},
        "real_send": (truth.get(pid) or {}).get("matt_sent", ""),
    })

DATA = json.dumps(items, ensure_ascii=False)

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Voice Tagger __BATCH__</title>
<style>
  :root{
    --bg:#0f1419; --panel:#161c24; --panel2:#1c242e; --ink:#e6edf3; --dim:#8b97a6;
    --line:#283341; --accent:#4f8cff; --pick:#1f6f43; --pickline:#2ea36a;
    --aOnly:#5a1e2b; --bOnly:#1f4d33; --note:#23303d;
  }
  *{box-sizing:border-box}
  html,body{margin:0;background:var(--bg);color:var(--ink);
    font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
  header{position:sticky;top:0;z-index:5;background:var(--panel);border-bottom:1px solid var(--line);
    padding:10px 18px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
  header h1{font-size:14px;margin:0;font-weight:700;letter-spacing:.3px}
  header .dim{color:var(--dim);font-size:13px}
  .bar{flex:1;min-width:160px;height:8px;background:var(--panel2);border-radius:6px;overflow:hidden}
  .bar>i{display:block;height:100%;background:var(--accent);width:0;transition:width .2s}
  .btns{display:flex;gap:8px;flex-wrap:wrap}
  button{background:var(--panel2);color:var(--ink);border:1px solid var(--line);border-radius:8px;
    padding:7px 12px;font-size:13px;cursor:pointer}
  button:hover{border-color:var(--accent)}
  button.on{background:var(--accent);border-color:var(--accent);color:#fff}
  main{max-width:1180px;margin:0 auto;padding:18px}
  .ctx{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin-bottom:14px}
  .ctx .meta{color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
  .ctx .q{font-size:13px;color:var(--accent);margin-top:6px;font-weight:600}
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  @media(max-width:880px){.cols{grid-template-columns:1fr}}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
  .card .top{display:flex;align-items:center;justify-content:space-between;padding:9px 14px;border-bottom:1px solid var(--line)}
  .card .lab{font-weight:800;font-size:15px}
  .card.pick{border-color:var(--pickline);box-shadow:0 0 0 1px var(--pickline) inset}
  .card.pick .top{background:var(--pick)}
  .msg{margin:0;padding:14px;white-space:pre-wrap;word-wrap:break-word;
    font:13px/1.55 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#dbe5ef;flex:1}
  .msg ins{background:var(--bOnly);text-decoration:none;border-radius:3px}
  .msg del{background:var(--aOnly);text-decoration:none;border-radius:3px}
  .pickbtn{width:100%;border:0;border-top:1px solid var(--line);border-radius:0;padding:11px;font-weight:700;font-size:14px}
  .note{width:100%;margin-top:12px;background:var(--note);color:var(--ink);border:1px solid var(--line);
    border-radius:8px;padding:10px 12px;font-size:13px;resize:vertical;min-height:42px}
  .ref{margin-top:12px;background:var(--panel2);border:1px dashed var(--line);border-radius:10px;overflow:hidden}
  .ref .top{padding:9px 14px;color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.5px}
  .ref pre{margin:0;padding:0 14px 14px;white-space:pre-wrap;font:13px/1.55 ui-monospace,Menlo,monospace;color:#c5d0db}
  .legend{color:var(--dim);font-size:12px;margin-top:18px;text-align:center}
  kbd{background:var(--panel2);border:1px solid var(--line);border-bottom-width:2px;border-radius:5px;padding:1px 6px;font:12px ui-monospace,monospace;color:var(--ink)}
  .done{text-align:center;padding:40px 16px}
  .done h2{color:var(--pickline)}
  .pill{display:inline-block;background:var(--panel2);border:1px solid var(--line);border-radius:20px;padding:3px 10px;margin:3px;font-size:12px;color:var(--dim)}
</style></head>
<body>
<header>
  <h1>VOICE TAGGER</h1><span class="dim" id="batch"></span>
  <div class="bar"><i id="prog"></i></div>
  <span class="dim" id="count"></span>
  <div class="btns">
    <button id="diffBtn" class="on" title="d">diff</button>
    <button id="refBtn" title="r">reference</button>
    <button id="exportBtn" title="e">export</button>
  </div>
</header>
<main id="app"></main>
<script>
const DATA = __DATA__;
const BATCH = "__BATCH__";
const LS = "voicetag:"+BATCH;
let state = JSON.parse(localStorage.getItem(LS) || "null") || {idx:0, picks:{}, diff:true, ref:false};
state.diff = state.diff!==false;
function save(){localStorage.setItem(LS, JSON.stringify(state));}

// ---- word-level diff (LCS over tokens, whitespace preserved) ----
function tok(s){return s.split(/(\s+)/);}
function diff(a,b){
  const A=tok(a),B=tok(b),n=A.length,m=B.length;
  const dp=Array.from({length:n+1},()=>new Int32Array(m+1));
  for(let i=n-1;i>=0;i--)for(let j=m-1;j>=0;j--)
    dp[i][j]=A[i]===B[j]?dp[i+1][j+1]+1:Math.max(dp[i+1][j],dp[i][j+1]);
  const aOut=[],bOut=[];let i=0,j=0;
  while(i<n&&j<m){
    if(A[i]===B[j]){aOut.push(['=',A[i]]);bOut.push(['=',B[j]]);i++;j++;}
    else if(dp[i+1][j]>=dp[i][j+1]){aOut.push(['-',A[i]]);i++;}
    else{bOut.push(['+',B[j]]);j++;}
  }
  while(i<n){aOut.push(['-',A[i]]);i++;}
  while(j<m){bOut.push(['+',B[j]]);j++;}
  return [aOut,bOut];
}
const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function renderDiffed(parts,kind){ // kind 'a' or 'b'
  return parts.map(([op,t])=>{
    if(op==='=')return esc(t);
    if(op==='-'&&kind==='a')return '<del>'+esc(t)+'</del>';
    if(op==='+'&&kind==='b')return '<ins>'+esc(t)+'</ins>';
    return '';
  }).join('');
}

function render(){
  const app=document.getElementById('app');
  document.getElementById('batch').textContent=BATCH+"  ·  "+DATA.length+" items";
  const done=Object.keys(state.picks).length;
  document.getElementById('count').textContent=done+" / "+DATA.length+" tagged";
  document.getElementById('prog').style.width=(100*done/DATA.length)+"%";
  document.getElementById('diffBtn').className=state.diff?'on':'';
  document.getElementById('refBtn').className=state.ref?'on':'';

  if(state.idx>=DATA.length){
    app.innerHTML='<div class="done"><h2>All '+DATA.length+' tagged.</h2>'+
      '<p class="dim">Press <kbd>e</kbd> or click export. The file downloads to your Downloads folder, then tell Claude it\'s done.</p>'+
      '<div>'+DATA.map((d,i)=>{const p=state.picks[d.item];return '<span class="pill">'+(i+1)+': '+(p?p.pick:'—')+'</span>';}).join('')+'</div>'+
      '<p style="margin-top:20px"><button id="exp2">Export picks</button> <button id="back">Back to last</button></p></div>';
    document.getElementById('exp2').onclick=doExport;
    document.getElementById('back').onclick=()=>{state.idx=DATA.length-1;save();render();};
    return;
  }
  const d=DATA[state.idx];
  const cur=state.picks[d.item]||{};
  let aHtml,bHtml;
  if(state.diff){const [ap,bp]=diff(d.A.text,d.B.text);aHtml=renderDiffed(ap,'a');bHtml=renderDiffed(bp,'b');}
  else{aHtml=esc(d.A.text);bHtml=esc(d.B.text);}
  const card=(lab,bodyHtml)=>{
    const picked=cur.pick===lab;
    return '<div class="card'+(picked?' pick':'')+'"><div class="top"><span class="lab">'+lab+'</span>'+
      (picked?'<span class="dim">your pick</span>':'')+'</div>'+
      '<pre class="msg">'+bodyHtml+'</pre>'+
      '<button class="pickbtn" data-pick="'+lab+'">pick '+lab+'  ('+lab.toLowerCase()+')</button></div>';
  };
  app.innerHTML=
    '<div class="ctx"><div class="meta">Item '+d.item+' of '+DATA.length+'  ·  '+esc(d.channel)+'  ·  to '+esc(d.recipient)+'</div>'+
    '<div>'+esc(d.context)+'</div><div class="q">Which is more you, A or B?  (diff highlights what changed)</div></div>'+
    '<div class="cols">'+card('A',aHtml)+card('B',bHtml)+'</div>'+
    '<textarea class="note" id="note" placeholder="why? (optional, press n)">'+esc(cur.note||'')+'</textarea>'+
    (state.ref?('<div class="ref"><div class="top">reference: what you actually sent (not part of the choice)</div><pre>'+esc(d.real_send||'(none captured)')+'</pre></div>'):'')+
    '<div class="legend"><kbd>a</kbd>/<kbd>b</kbd> pick &nbsp; <kbd>t</kbd> tie &nbsp; <kbd>&larr;</kbd><kbd>&rarr;</kbd> move &nbsp; <kbd>d</kbd> diff &nbsp; <kbd>r</kbd> reference &nbsp; <kbd>n</kbd> note &nbsp; <kbd>e</kbd> export</div>';
  document.querySelectorAll('.pickbtn').forEach(b=>b.onclick=()=>pick(b.dataset.pick));
  const note=document.getElementById('note');
  note.addEventListener('input',()=>{const c=state.picks[d.item]||{};c.note=note.value;state.picks[d.item]=c;save();});
}
function pick(letter){
  const d=DATA[state.idx];
  const src=d[letter]?d[letter].source:null;
  const prev=state.picks[d.item]||{};
  state.picks[d.item]={pick:letter,picked_source:src,id:d.id,note:prev.note||document.getElementById('note')?.value||''};
  save();
  setTimeout(()=>{state.idx=Math.min(state.idx+1,DATA.length);save();render();},140);
  render();
}
function nav(delta){state.idx=Math.max(0,Math.min(DATA.length,state.idx+delta));save();render();}
function doExport(){
  const out={batch:BATCH,n:DATA.length,tagged:Object.keys(state.picks).length,
    picks:DATA.map(d=>{const p=state.picks[d.item]||{};return {item:d.item,id:d.id,pick:p.pick||null,picked_source:p.picked_source||null,note:p.note||""};})};
  const blob=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='voice-picks-'+BATCH+'.json';a.click();
  navigator.clipboard&&navigator.clipboard.writeText(JSON.stringify(out)).catch(()=>{});
}
document.getElementById('diffBtn').onclick=()=>{state.diff=!state.diff;save();render();};
document.getElementById('refBtn').onclick=()=>{state.ref=!state.ref;save();render();};
document.getElementById('exportBtn').onclick=doExport;
document.addEventListener('keydown',e=>{
  if(e.target.tagName==='TEXTAREA'){if(e.key==='Escape')e.target.blur();return;}
  const k=e.key.toLowerCase();
  if(k==='a'||k==='1'){pick('A');}
  else if(k==='b'||k==='2'){pick('B');}
  else if(k==='t'){pick('tie');}
  else if(e.key==='ArrowRight'){nav(1);}
  else if(e.key==='ArrowLeft'){nav(-1);}
  else if(k==='d'){state.diff=!state.diff;save();render();}
  else if(k==='r'){state.ref=!state.ref;save();render();}
  else if(k==='n'){const n=document.getElementById('note');if(n){e.preventDefault();n.focus();}}
  else if(k==='e'){doExport();}
});
render();
</script>
</body></html>
"""

html_out = (TEMPLATE
            .replace("__DATA__", DATA)
            .replace("__BATCH__", batch))
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(html_out, encoding="utf-8")
print(f"wrote {out_path}  ({len(items)} items, {len(html_out)} bytes)")
