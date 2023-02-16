rm -rf saved
rm returnData.json
git add .
git commit -m 'Commit'
git pull origin main
git push origin main
git pull heroku main
git push heroku main