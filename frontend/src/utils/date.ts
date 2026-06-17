/**
 * Formats a Date object into a user-friendly string.
 * Example format: "11 Jun 2026, 10:30 AM"
 * 
 * @param date The date to format
 * @returns The formatted date string
 */
export function formatLastUpdated(date: Date): string {
  const day = date.getDate();
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const month = months[date.getMonth()];
  const year = date.getFullYear();

  let hours = date.getHours();
  const minutes = date.getMinutes().toString().padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12;
  hours = hours ? hours : 12; // convert 0 to 12

  return `${day} ${month} ${year}, ${hours}:${minutes} ${ampm}`;
}
