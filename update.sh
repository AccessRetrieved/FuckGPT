rm -rf saved
rm returnData.json
git pull
git add .
git commit -m 'Commit'
git push origin main
git push heroku main