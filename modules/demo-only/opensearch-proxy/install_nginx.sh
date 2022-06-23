#!/bin/bash

export OS_E=$1
export USR=$2
export PWD=$3

echo $OS_E


sudo yum install httpd-tools -y
sudo mkdir /home/pwd
echo $PWD | htpasswd -i -c /home/pwd/.htpasswd $USR

sudo amazon-linux-extras install nginx1 -y
sudo systemctl enable nginx

sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -subj "/C=US/ST=Denial/L=Seattle/O=Dis/CN=addf.amazondomains.com" \
    -keyout /etc/nginx/cert.key -out /etc/nginx/cert.crt

cat > /etc/nginx/conf.d/default.conf <<EOF
server {
    listen 443;
    server_name \$host;
    rewrite ^/$ https://\$host/_dashboards redirect;

    auth_basic "ADDF Opensearch Proxy";
    auth_basic_user_file /home/pwd/.htpasswd;
    ssl_certificate           /etc/nginx/cert.crt;
    ssl_certificate_key       /etc/nginx/cert.key;

    ssl on;
    ssl_session_cache  builtin:1000  shared:SSL:10m;
    ssl_protocols  TLSv1.2;
    ssl_ciphers HIGH:!aNULL:!eNULL:!EXPORT:!CAMELLIA:!DES:!MD5:!PSK:!RC4;
    ssl_prefer_server_ciphers on;

    location /_dashboards {
        proxy_set_header Authorization "";
        proxy_pass https://domain-endpoint;
        proxy_pass_header Authorization;
        proxy_cookie_domain domain-endpoints \$host;
        proxy_cookie_path / /_dashboards/;
        proxy_set_header Accept-Encoding "";
        sub_filter_types *;
        sub_filter domain-endpoint \$host;
        sub_filter_once off;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
    location ~ \/(log|sign|error|fav|forgot|change) {
        proxy_redirect https://domain-endpoint https://\$host;
    }
}
EOF


sudo sed -i "s/domain-endpoint/$OS_E/" /etc/nginx/conf.d/default.conf
sudo systemctl restart nginx