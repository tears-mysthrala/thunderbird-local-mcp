import pathlib, sys, zipfile, json
root = pathlib.Path(sys.argv[1]).resolve()
with zipfile.ZipFile(root/('dist/thunderbird-local-mcp-'+json.loads((root/'extension/manifest.json').read_text(encoding='utf-8-sig'))['version']+'.xpi'),'w',zipfile.ZIP_DEFLATED) as output:
    for path in sorted((root/'extension').glob('*')):
        if path.is_file() and path.name!='config.js':
            output.write(path,path.name)

manifest=json.loads((root/'extension/manifest.json').read_text(encoding='utf-8-sig'))
version=manifest['version']
asset=root/f'dist/thunderbird-local-mcp-{version}.xpi'
import hashlib
entry={'version':version,'update_link':f'https://github.com/tears-mysthrala/thunderbird-local-mcp/releases/download/v{version}/{asset.name}','update_hash':'sha256:'+hashlib.sha256(asset.read_bytes()).hexdigest(),'applications':{'gecko':{'strict_min_version':'147.0'}}}
(root/'updates.json').write_text(json.dumps({'addons':{manifest['browser_specific_settings']['gecko']['id']:{'updates':[entry]}}},indent=2)+'\n',encoding='utf-8',newline='\n')
