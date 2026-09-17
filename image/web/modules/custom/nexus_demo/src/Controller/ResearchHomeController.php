<?php

namespace Drupal\nexus_demo\Controller;

use Drupal\Core\Controller\ControllerBase;
use Drupal\node\NodeInterface;

/**
 * Builds the Nexus Research demo homepage.
 */
final class ResearchHomeController extends ControllerBase {

  /**
   * Returns the visual research homepage.
   */
  public function build(): array {
    return [
      '#theme' => 'nexus_home',
      '#projects' => $this->loadCards('project'),
      '#people' => $this->loadCards('person'),
      '#events' => $this->loadCards('event'),
      '#cache' => [
        'tags' => ['node_list'],
        'contexts' => ['user.permissions'],
      ],
    ];
  }

  /**
   * Loads published demo nodes and normalizes them for Twig.
   */
  private function loadCards(string $bundle): array {
    $ids = $this->entityTypeManager()->getStorage('node')->getQuery()
      ->accessCheck(TRUE)
      ->condition('type', $bundle)
      ->condition('status', 1)
      ->sort('created', 'ASC')
      ->range(0, 3)
      ->execute();

    $cards = [];
    foreach ($this->entityTypeManager()->getStorage('node')->loadMultiple($ids) as $node) {
      $cards[] = $this->normalizeCard($node, $bundle);
    }
    return $cards;
  }

  /**
   * Converts a node into a small presentation-neutral card array.
   */
  private function normalizeCard(NodeInterface $node, string $bundle): array {
    $card = [
      'title' => $node->label(),
      'url' => $node->toUrl()->toString(),
    ];

    if ($bundle === 'project') {
      $area = $node->get('field_research_area')->first();
      $status = $node->get('field_project_status')->first();
      $card += [
        'summary' => $node->get('field_project_summary')->value,
        'area' => $area?->getPossibleOptions()[$area->value] ?? $area?->value,
        'status' => $status?->getPossibleOptions()[$status->value] ?? $status?->value,
        'accent' => $area?->value ?? 'computing',
      ];
    }
    elseif ($bundle === 'person') {
      $card += [
        'role' => $node->get('field_role')->value,
        'biography' => $node->get('field_biography')->value,
      ];
    }
    elseif ($bundle === 'event') {
      $date = new \DateTimeImmutable($node->get('field_event_date')->value, new \DateTimeZone('UTC'));
      $card += [
        'month' => strtoupper($date->format('M')),
        'day' => $date->format('d'),
        'date' => $date->format('j F Y · H:i'),
        'location' => $node->get('field_location')->value,
      ];
    }

    return $card;
  }

}
