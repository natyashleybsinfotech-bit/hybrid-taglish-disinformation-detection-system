const RECOMMENDATION_HEADINGS = /\b(?:people you may know|people you might know|suggested friends|friend suggestions|suggested for you)\b/i;
const FRIEND_ACTION = /^(?:add friend|confirm friend|send friend request)$/i;

export function isRecommendationSurface({ headings = [], labels = [], pagelets = [] } = {}) {
  const normalizedPagelets = pagelets.map(value => (value || '').replace(/([a-z])([A-Z])/g, '$1 $2').replace(/[_-]/g, ' '));
  if ([...headings, ...labels, ...normalizedPagelets].some(value => RECOMMENDATION_HEADINGS.test(value || ''))) return true;
  const friendActions = labels.filter(value => FRIEND_ACTION.test((value || '').trim()));
  return friendActions.length >= 2;
}
