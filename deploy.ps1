$server = "root@137.184.156.11"
$app_dir = "/var/www/appraisalsystem"

Write-Host "Deploying Appraisal System..." -ForegroundColor Green

# The deployment script will SSH into the server and run the update commands
ssh $server "cd $app_dir && git pull origin main && source .venv/bin/activate && pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput && systemctl restart appraisalsystem && systemctl restart nginx"

if ($?) {
    Write-Host "Deployment completed successfully!" -ForegroundColor Green
} else {
    Write-Host "Deployment failed. Please check the logs above." -ForegroundColor Red
}
