$headers = @{Origin='http://localhost:5175'; 'Content-Type'='application/json'}
$body = '{"name":"autotest","email":"autotest@example.com","password":"secret"}'
$response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/auth/signup' -Method POST -Headers $headers -Body $body -UseBasicParsing
Write-Host $response.StatusCode
Write-Host $response.Content
Write-Host $response.Headers['Access-Control-Allow-Origin']
