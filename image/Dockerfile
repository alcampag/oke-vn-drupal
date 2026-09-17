# Pinned official PHP 8.4/Apache base; Composer installs Drupal 11.4.7.
FROM drupal:11.4.5-php8.4-apache-bookworm@sha256:a39359c2e112ded47875888705613d16673399af5acf3a7d7e11553e5059d6d4
WORKDIR /opt/drupal
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-interaction --prefer-dist --optimize-autoloader \
    && composer audit --no-dev
COPY --chown=www-data:www-data --chmod=0444 settings.php /opt/drupal/web/sites/default/settings.php
COPY --chown=www-data:www-data --chmod=0444 healthz.html /opt/drupal/web/healthz.html
COPY --chown=www-data:www-data web/modules/custom/nexus_demo /opt/drupal/web/modules/custom/nexus_demo
COPY --chown=www-data:www-data web/themes/custom/nexus_theme /opt/drupal/web/themes/custom/nexus_theme
# Keep the official image's entrypoint and command.
