FROM nginx:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/
COPY styles.css /usr/share/nginx/html/
COPY app.js /usr/share/nginx/html/
COPY vendor/katex/ /usr/share/nginx/html/vendor/katex/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
