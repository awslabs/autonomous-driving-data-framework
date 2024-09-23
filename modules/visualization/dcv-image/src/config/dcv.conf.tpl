###############################################################################
## Section "license" contains properties to configure the the license management
###############################################################################

[license]

# Property "license-file" specifies the path to a demo license file or the name
# of the license server used by the rlm daemon, in the format port@host
# (for example 5053@licserver).
# The port number must be the same as that specified in the HOST line of the
# license file.
# If empty or not specified, a default path to a demo license file will be
# used (e.g: /usr/share/dcv/license/license.lic). If the default file does not
# exists a demo license will be used.
license-file = "/etc/dcv/license.lic"

###############################################################################
## Section "log" contains properties to configure the DCV logging system
###############################################################################

[log]

# Property "level" contains the logging level used by DCV.
# Can be set to ERROR, WARNING, INFO or DEBUG (in ascending level of verbosity).
# If not specified, the default level is INFO
level = "DEBUG"
log_file = /var/log/nice-dcv/dcv-session-manager.log

###############################################################################
## Section "session-management" contains the properties of DCV session creation
###############################################################################

[session-management]

# Property "create-session" requests to automatically create a console session
# (with ID "console") at DCV startup.
# Can be set to true or false.
# If not specified, no console session will be automatically created.
# create-session = true
# virtual-session-xdcv-args="-listen tcp"

# Property "enable-gl-in-virtual-sessions" specifies whether to employ the
# 'dcv-gl' feature (a specific license will be required).
# Allowed values: 'always-on', 'always-off', 'default-on', 'default-off'.
# If not specified, the default value is 'default-on'.
enable-gl-in-virtual-sessions = "default-on"

###############################################################################
## Section "session-management/defaults" contains the default properties of DCV sessions
###############################################################################

[session-management/defaults]

# Property "permissions-file" specifies the path to the permissions file
# automatically merged with the permissions selected by the user for each session.
# If empty or absent, use the default file in /etc/dcv/default.perm.
#permissions-file = ""

###############################################################################
## Section "session-management.automatic-console-session" contains the properties
## to be applied ONLY to the "console" session automatically created at server startup
## when the create-session setting of section 'session-management' is set to true.
###############################################################################

[session-management/automatic-console-session]

# Property "owner" specifies the username of the owner of the automatically
# created "console" session.
# owner = "user"

# Property "permissions-file" specifies the file that contains the permissions
# to be used to check user access to DCV features.
# If empty, only the owner will have full access to the session.
#permissions-file = ""

# Property "max-concurrent-clients" specifies the maximum number of concurrent
# clients per session.
# If set to -1, no limit is enforced. Default value -1;
max-concurrent-clients = 1

# Property "storage-root" specifies the path to the folder that will be used
# as root-folder for file storage operations.
# The file storage will be disabled if the storage-root is empty or the folder
# does not exist.
storage-root = "/home/ubuntu/Uploaded"

###############################################################################
## Section "display" contains the properties of the dcv remote display
###############################################################################

[display]

# Property "target-fps" specifies which is the upper limit to the frames per
# second that are sent to the client. A higher value consumes more bandwidth
# and resources. By default it is set to 25. Set to 0 for no limit
target-fps = 25
# session-start-command="/usr/local/bin/startup_script.sh" # default?
gl-displays = [':0.0']

###############################################################################
## Section "connectivity" contains the properties of the dcv connection
###############################################################################

[connectivity]
# Property "web-port" specifies on which TCP port the DCV server listens on
# It must be a number between 1024 and 65535 representing an
# available TCP port on which the web server embedded in the DCV Server will
# listen for connection requests to serve HTTP(S) pages and WebSocket
# connections
# If not specified, DCV will use port 8443
#web-port=8444
enable-quic-frontend=true

# Property "web-url-path" specifies a URL path for the embedded web server.
# The path must start with /. For instance setting it to "/test/foo" means the
# web server will be reachable at https://host:port/test/foo.
# This property is especially useful when setting up a gateway that then
# routes each connection to a different DCV server.
# If not specified DCV uses "/", which means it will be reachable at
# https://host:port
#web-url-path="/dcv"

# Property "idle-timeout" specifies a timeout in minutes after which
# a client that does not send keyboard or mouse events is considered idle
# and hence disconnected.
# By default it is set to 60 (1 hour). Set to 0 to never disconnect
# idle clients.
idle-timeout=60

###############################################################################
## Section "security" contains the properties related to authentication and security
###############################################################################

[security]

# Property "authentication" specifies the client authentication method used by
# the DCV server. Use 'system' to delegate client authentication to the
# underlying operating system. Use 'none' to disable client authentication and
# grant access to all clients.
#authentication="none"

# Property "pam-service-name" specifies the name of the PAM configuration file
# used by DCV. The default PAM service name is 'dcv' and corresponds with
# the /etc/pam.d/dcv configuration file. This parameter is only used if
# the 'system' authentication method is used.
#pam-service-name="dcv-custom"

# Property "auth-token-verifier" specifies an endpoint (URL) for an external
# the authentication token verifier. If empty or not specified, the internal
# authentication token verifier is used
# auth-token-verifier="http://${AUTH_SERVICE_NAME}.${AUTH_NAMESPACE}.svc.cluster.local:${AUTH_PORT}"

# Session Manager: https://docs.aws.amazon.com/dcv/latest/sm-admin/servers.html
# ca-file="/etc/dcv-session-manager-agent/broker_cert.pem"
administrators=["dcvsmagent"]

[clipboard]
primary-selection-paste=true
primary-selection-copy=true
