const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** A stored time: UTC, sometimes without a zone. */
export const parseTime = (iso: string) =>
  new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);

/** "Today 09:42", "Yesterday 18:05", "6 Nov 11:20", in the viewer's time zone. */
export const timeLabel = (iso: string) => {
  const date = parseTime(iso);
  const hm = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
  const startOf = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((startOf(new Date()) - startOf(date)) / 864e5);
  const day =
    days === 0 ? 'Today' : days === 1 ? 'Yesterday' : `${date.getDate()} ${MONTHS[date.getMonth()]}`;
  return `${day} ${hm}`;
};

/** "1:13" */
export const clock = (seconds: number) => {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
};

/** "820 ms", "3.1 s" */
export const shortDuration = (ms: number) => (ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`);
