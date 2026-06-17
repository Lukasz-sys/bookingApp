@echo off
echo === System rezerwacji wizyt: Docker full stack ===
for %%C in (booking_postgres booking_api booking_frontend) do (
  docker ps -aq --filter "name=^/%%C$" > .docker_container_check.tmp
  set /p CID=<.docker_container_check.tmp
  if not "%%CID%%"=="" docker rm -f %%CID%%
  del .docker_container_check.tmp >NUL 2>NUL
)
docker compose down --remove-orphans -v
docker compose build --no-cache
if errorlevel 1 exit /b 1
docker compose up -d --force-recreate
if errorlevel 1 exit /b 1
echo.
echo Gotowe.
echo Frontend: http://localhost:8080
echo CSS test: http://localhost:8080/styles.css
echo API:      http://localhost:8000/health
echo Docs:     http://localhost:8000/docs
echo.
echo Jezeli przegladarka pokazuje stara wersje bez styli: Ctrl + F5.
