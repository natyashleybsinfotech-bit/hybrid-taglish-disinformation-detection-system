// The primary UI lives in the popup. Content scripts only extract text after
// an explicit message from that UI; they never classify or observe posts.
export { default } from './Popup.jsx';
