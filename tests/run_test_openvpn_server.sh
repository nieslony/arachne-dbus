#/bin/bash

OPENVPN_DIR=/tmp/openvpn-server
LISTEN="192.168.199.0 255.255.255.0"

CA_KEY=$OPENVPN_DIR/ca.key
CA_CERT=$OPENVPN_DIR/ca.crt
SERVER_KEY=$OPENVPN_DIR/server.key
SERVER_CERT=$OPENVPN_DIR/server.cert
SERVER_CSR=$OPENVPN_DIR/server.csr
DH_PARAMS=$OPENVPN_DIR/dh.pem
STATUS_FILE=$OPENVPN_DIR/status-arachne-site.log

log() {
  echo
  echo "--- $(date) --- $@ ---"
}

if [ ! -d "$OPENVPN_DIR" ]; then
  log "Creating $OPENVPN_DIR"
  mkdir -v "$OPENVPN_DIR" || exit 1
fi

if [ ! -e "$CA_KEY" -o ! -e "$CA_CERT" ]; then
  log "Creating CA certificate and key"
  openssl \
      req -x509 \
      -new \
      -nodes \
      -newkey rsa:2048 \
      -keyout "$CA_KEY" \
      -out "$CA_CERT" \
      -subj "/CN=Test_CA"
fi

if [ ! -e "$SERVER_KEY" ]; then
  log "Create server key $SERVER_KEY"
  openssl genrsa -out $SERVER_KEY -verbose
fi

if [ ! -e "$SERVER_CERT" ]; then
  log "Create CSR $SERVER_CSR"
  openssl req -new \
    -key $SERVER_KEY -out $SERVER_CSR \
    -subj "/CN=$HOSTNAME" \
    -verbose

  log "Sign CSR"
  openssl x509 -req \
    -in $SERVER_CSR \
    -CA $CA_CERT \
    -CAkey $CA_KEY \
    -CAcreateserial \
    -out $SERVER_CERT \
    -days 365 \
    -sha256
fi

if [ ! -e $DH_PARAMS ]; then
  log "Creating DH params"
  openssl dhparam -dsaparam -out $DH_PARAMS 2048
fi

log "Starting openvpn as root"
CMD="openvpn --server $192.168.199.0 255.255.255.0 \
  --topology subnet \
  --dev tun \
  --ca $CA_CERT \
  --cert $SERVER_CERT --key $SERVER_KEY \
  --dh $DH_PARAMS \
  --status-version 2 --status $STATUS_FILE
"
echo "Starting $CMD"
touch /tmp/openvpn-server/status-arachne-site.log
sudo $CMD

