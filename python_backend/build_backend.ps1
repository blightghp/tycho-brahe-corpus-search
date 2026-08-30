# Script para compilar o backend Python em um executável (.exe)
# Isso permite que o aplicativo Tauri chame o Python sem precisar do ambiente Python instalado na máquina do usuário.

Write-Host "Compilando pesquisa_sintatica.py..."
C:\Users\Administrador\AppData\Roaming\Python\Python313\Scripts\pyinstaller.exe --onefile --name "tycho_backend" pesquisa_sintatica.py

Write-Host "Copiando executável para src-tauri/bin..."
New-Item -ItemType Directory -Force "../tycho-desktop/src-tauri/bin"
Copy-Item "dist/tycho_backend.exe" -Destination "../tycho-desktop/src-tauri/bin/tycho_backend-x86_64-pc-windows-msvc.exe" -Force

Write-Host "Build do backend concluído!"
