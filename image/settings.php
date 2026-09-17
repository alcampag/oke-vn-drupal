<?php

$databases['default']['default'] = [
  'database' => getenv('DRUPAL_DB_NAME'),
  'username' => getenv('DRUPAL_DB_USER'),
  'password' => getenv('DRUPAL_DB_PASSWORD'),
  'host' => getenv('DRUPAL_DB_HOST'),
  'port' => getenv('DRUPAL_DB_PORT') ?: '3306',
  'driver' => 'mysql',
  'prefix' => '',
];

$settings['hash_salt'] = getenv('DRUPAL_HASH_SALT');
$settings['file_public_path'] = 'sites/default/files';
$settings['file_private_path'] = '/var/www/html/sites/default/files/private';
$settings['config_sync_directory'] = '/var/www/html/sites/default/files/config-sync';

$proxyAddresses = json_decode(getenv('DRUPAL_REVERSE_PROXY_ADDRESSES') ?: '[]', true);
if (is_array($proxyAddresses) && $proxyAddresses) {
  $settings['reverse_proxy'] = TRUE;
  $settings['reverse_proxy_addresses'] = $proxyAddresses;
  $settings['reverse_proxy_trusted_headers'] =
    \Symfony\Component\HttpFoundation\Request::HEADER_X_FORWARDED_FOR |
    \Symfony\Component\HttpFoundation\Request::HEADER_X_FORWARDED_PROTO |
    \Symfony\Component\HttpFoundation\Request::HEADER_X_FORWARDED_PORT;
}

$trustedHostPatterns = json_decode(
  getenv('DRUPAL_TRUSTED_HOST_PATTERNS') ?: '[".*"]',
  true,
);
$settings['trusted_host_patterns'] = is_array($trustedHostPatterns)
  ? $trustedHostPatterns
  : ['.*'];
