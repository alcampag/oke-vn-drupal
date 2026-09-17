<?php
// Never print connection strings, SQL statements, or credential-bearing errors.
try {
  $host = getenv('DRUPAL_DB_HOST');
  $port = getenv('DRUPAL_DB_PORT') ?: '3306';
  $name = getenv('DRUPAL_DB_NAME');
  if (!preg_match('/^[a-zA-Z0-9_]+$/', $name)) {
    throw new RuntimeException('Invalid database identifier');
  }
  if (getenv('MYSQL_ADMIN_USER') && !in_array('--require-empty', $argv, true)) {
    $admin = new PDO("mysql:host=$host;port=$port", getenv('MYSQL_ADMIN_USER'), getenv('MYSQL_ADMIN_PASSWORD'), [PDO::ATTR_TIMEOUT => 10]);
    $user = $admin->quote(getenv('DRUPAL_DB_USER'))."@'%'";
    $password = $admin->quote(getenv('DRUPAL_DB_PASSWORD'));
    $admin->exec("CREATE DATABASE IF NOT EXISTS `$name` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
    $admin->exec("CREATE USER IF NOT EXISTS $user IDENTIFIED BY $password");
    $admin->exec("GRANT ALL PRIVILEGES ON `$name`.* TO $user");
  }
  $db = new PDO("mysql:host=$host;port=$port;dbname=$name", getenv('DRUPAL_DB_USER'), getenv('DRUPAL_DB_PASSWORD'), [PDO::ATTR_TIMEOUT => 10]);
  if (in_array('--require-empty', $argv, true)) {
    $count = (int) $db->query('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()')->fetchColumn();
    if ($count !== 0) {
      fwrite(STDERR, "Refusing to reinstall Drupal over a nonempty database.\n");
      exit(1);
    }
  }
  echo "Database check passed.\n";
} catch (Throwable $error) {
  fwrite(STDERR, "Database check failed; code ".$error->getCode().". Check the host, credentials, and grants.\n");
  exit(1);
}
