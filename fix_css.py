with open('src/fabrizon/gui_page.py', 'r') as f:
    content = f.read()

# Find the exact old section
idx = content.find('.toast.ok{border-left:4px solid var(--ok)}')
if idx == -1:
    print('NOT FOUND')
    exit(1)

# Find the end of the section we want to replace
end_marker = '<div class="wrap">'
end_idx = content.find(end_marker, idx)
if end_idx == -1:
    print('END MARKER NOT FOUND')
    exit(1)

end_idx += len(end_marker)

old_section = content[idx:end_idx]
print('OLD SECTION:')
print(repr(old_section))

new_section = """}
.toast.ok{border-left:4px solid var(--ok)}
.toast.err{border-left:4px solid var(--bad)}
.toast.warn{border-left:4px solid var(--warn)}
@keyframes slideIn{from{opacity:0; transform:translateX(20px)}to{opacity:1; transform:translateX(0)}}

/* ===== Settings Tab ===== */
#t-settings{padding-top:8px}
.settings-grid{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
  gap:16px; margin-bottom:16px;
}
.setting-group{
  background:var(--panel2); border:1px solid var(--line);
  border-radius:10px; padding:16px;
}
.setting-group h3{margin:0 0 12px; font-size:13px; color:var(--mute); text-transform:uppercase; letter-spacing:.5px}
.setting-row{display:flex; flex-direction:column; gap:6px; margin-bottom:12px}
.setting-row label{margin:0; font-size:12px; font-weight:600; color:var(--text)}
.setting-row .hint{font-size:11px; color:var(--mute); margin-top:2px}
.setting-row input[type=text], .setting-row input[type=password]{
  background:var(--panel); border:1px solid var(--line);
  border-radius:8px; padding:10px 12px; color:var(--text); font:inherit;
}
.setting-row input[type=text]:focus, .setting-row input[type=password]:focus{
  outline:none; border-color:var(--accent); box-shadow:0 0 0 3px rgba(109,126,255,.15)
}
.setting-actions{display:flex; gap:8px; margin-top:8px}
.status-indicator{display:inline-flex; align-items:center; gap:6px; padding:6px 12px; border-radius:6px; font-size:12px; font-weight:600}
.status-indicator.ok{background:var(--ok-bg); color:var(--ok); border:1px solid rgba(56,217,169,.25)}
.status-indicator.warn{background:var(--warn-bg); color:var(--warn); border:1px solid rgba(255,195,90,.25)}
.status-indicator.err{background:var(--bad-bg); color:var(--bad); border:1px solid rgba(255,107,122,.25)}
.status-indicator .dot{width:8px; height:8px; border-radius:50%}
.status-indicator.ok .dot{background:var(--ok)}
.status-indicator.warn .dot{background:var(--warn)}
.status-indicator.err .dot{background:var(--bad)}

/* Responsive */
@media (max-width:768px){
  .wrap{padding:24px 16px 60px}
  .kv{grid-template-columns:100px 1fr}
  .grid{grid-template-columns:repeat(2,1fr)}
  .stat .n{font-size:22px}
  th,td{padding:10px 8px}
  .tabs{flex-wrap:wrap}
}
</style></head>
<body>
<div class="wrap">"""

new_content = content[:idx] + new_section + content[end_idx:]

with open('src/fabrizon/gui_page.py', 'w') as f:
    f.write(new_content)

print('SUCCESS: CSS updated')