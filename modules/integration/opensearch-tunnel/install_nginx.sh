#!/bin/bash

export OS_E=$1
export PORT=$2

echo $OS_E
echo $PORT 

#sudo amazon-linux-extras install nginx1
sudo yum install -y nginx
sudo systemctl enable nginx

# Leaving this here in case someone wants to use a non-AL image
# sudo yum install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm
# sudo service amazon-ssm-agent restart

cat > /etc/nginx/conf.d/proxy.conf <<EOF
server {
    listen listen-port;
    server_name \$host;
    rewrite ^/$ http://\$host/_dashboards redirect;

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
        proxy_redirect https://domain-endpoint http://\$host;
    }
}
EOF


sudo sed -i "s/domain-endpoint/$OS_E/" /etc/nginx/conf.d/proxy.conf
sudo sed -i "s/listen-port/$PORT/" /etc/nginx/conf.d/proxy.conf
sudo systemctl restart nginx