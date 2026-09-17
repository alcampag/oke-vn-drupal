#!/bin/sh
set -eu
cd /opt/drupal
php /setup/database.php
if ! vendor/bin/drush status --field=bootstrap 2>/dev/null | grep -q Successful; then
  if [ "$INSTALL_IF_EMPTY" != "true" ]; then
    echo "Drupal is not installed; installIfEmpty is disabled." >&2
    exit 1
  fi
  php /setup/database.php --require-empty
  vendor/bin/drush site:install standard --site-name="$DRUPAL_SITE_NAME" \
    --account-name="$DRUPAL_ADMIN_USER" --account-pass="$DRUPAL_ADMIN_PASSWORD" \
    --account-mail="$DRUPAL_ADMIN_EMAIL" -y --quiet
fi
vendor/bin/drush pm:install nexus_demo -y
vendor/bin/drush updatedb -y
vendor/bin/drush cache:rebuild
vendor/bin/drush status --fields=drupal-version,bootstrap,db-status
php -r 'if (file_put_contents("web/sites/default/files/demo-storage-check.txt", "Shared FSS storage is working.\n") === false) { exit(1); }'
