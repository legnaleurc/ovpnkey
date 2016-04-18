import pkg_resources

index_html = pkg_resources.resource_filename(__name__, 'index.html')
gk_sh = pkg_resources.resource_filename(__name__, 'gk.sh')
client_ovpn = pkg_resources.resource_string(__name__, 'client.ovpn').decode('utf-8')
