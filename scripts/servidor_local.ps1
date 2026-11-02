# Servidor local do site (pasta web/) para Windows, sem instalar nada.
# Uso: de dois cliques em "abrir_site.bat" na raiz do projeto.
# Fecha com Ctrl+C ou fechando a janela.
$ErrorActionPreference = "Stop"
$raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\web")).Path
$porta = 8000
$tipos = @{
  ".html" = "text/html; charset=utf-8"; ".js" = "text/javascript; charset=utf-8";
  ".css" = "text/css; charset=utf-8"; ".json" = "application/json; charset=utf-8";
  ".png" = "image/png"; ".jpg" = "image/jpeg"; ".svg" = "image/svg+xml"; ".ico" = "image/x-icon"
}

$servidor = $null
foreach ($p in 8000..8010) {
  try {
    $servidor = New-Object System.Net.HttpListener
    $servidor.Prefixes.Add("http://localhost:$p/")
    $servidor.Start()
    $porta = $p
    break
  } catch { $servidor = $null }
}
if (-not $servidor) { Write-Host "Nao foi possivel abrir uma porta entre 8000 e 8010."; Read-Host "Enter para sair"; exit 1 }

$endereco = "http://localhost:$porta/"
Write-Host ""
Write-Host "  Site do Brasileirao 2024 rodando em $endereco"
Write-Host "  Deixe esta janela aberta enquanto usa o site. Para parar, feche a janela."
Write-Host ""
Start-Process $endereco

while ($servidor.IsListening) {
  $ctx = $servidor.GetContext()
  $caminho = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath).TrimStart("/")
  if ($caminho -eq "") { $caminho = "index.html" }
  $arquivo = [System.IO.Path]::GetFullPath((Join-Path $raiz $caminho))
  $resposta = $ctx.Response
  try {
    if ($arquivo.StartsWith($raiz) -and (Test-Path $arquivo -PathType Leaf)) {
      $bytes = [System.IO.File]::ReadAllBytes($arquivo)
      $ext = [System.IO.Path]::GetExtension($arquivo).ToLower()
      $resposta.ContentType = if ($tipos.ContainsKey($ext)) { $tipos[$ext] } else { "application/octet-stream" }
      $resposta.ContentLength64 = $bytes.Length
      $resposta.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
      $resposta.StatusCode = 404
    }
  } catch { } finally { $resposta.Close() }
}
