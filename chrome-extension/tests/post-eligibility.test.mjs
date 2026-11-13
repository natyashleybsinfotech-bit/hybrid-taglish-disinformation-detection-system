import assert from 'node:assert/strict';
import test from 'node:test';
import { isRecommendationSurface } from '../src/post_eligibility.js';

test('People You May Know and suggested-friend panels are not posts', () => {
  assert.equal(isRecommendationSurface({ headings: ['People you may know'] }), true);
  assert.equal(isRecommendationSurface({ pagelets: ['PeopleYouMayKnowFeedUnit'] }), true);
  assert.equal(isRecommendationSurface({ headings: ['Suggested friends'] }), true);
  assert.equal(isRecommendationSurface({ labels: ['Add friend', 'Add friend', 'Add friend'] }), true);
});

test('regular post headings and a single incidental friend action are not enough to exclude a post', () => {
  assert.equal(isRecommendationSurface({ headings: ['News update'], labels: ['Comment', 'Share'] }), false);
  assert.equal(isRecommendationSurface({ headings: ['Local community'], labels: ['Add friend', 'Comment'] }), false);
});
