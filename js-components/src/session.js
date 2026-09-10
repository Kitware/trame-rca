/**
 * Helpers around the trame client session.
 *
 * A "source" is anything exposing a `trame` reference: a Vue component instance
 * (`this`), a React props object, or `{ trame }`. When no explicit reference is
 * provided we fall back to the globally exposed `window.trame`.
 */

export function getTrame(source) {
  if (source && source.trame) {
    return source.trame;
  }
  return typeof window !== 'undefined' ? window.trame : null;
}

export function getSession(source) {
  return getTrame(source)?.client?.getConnection()?.getSession();
}

export function subscribe(session, topic, callback) {
  if (!session) {
    return null;
  }
  return session.subscribe(topic, callback);
}

export function unsubscribe(session, subscription) {
  if (session && subscription) {
    session.unsubscribe(subscription);
  }
}
