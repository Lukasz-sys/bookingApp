FROM nginx:1.27-alpine

COPY frontend/nginx/default.conf /etc/nginx/conf.d/default.conf

# Pliki frontendu są kopiowane w dwa miejsca:
# 1) /usr/share/nginx/html           -> działa http://localhost:8080/index.html i /styles.css
# 2) /usr/share/nginx/html/static    -> działa też stary adres /static/index.html i /static/styles.css
COPY frontend /usr/share/nginx/html
COPY frontend /usr/share/nginx/html/static

EXPOSE 80
