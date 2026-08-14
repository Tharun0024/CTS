import { mockRequest } from './api';
import { mockNotifications } from '../mock/notifications';
import type { Notification } from '../types/claim';

let notifStore: Notification[] = [...mockNotifications];

// GET /api/notifications
export async function getNotifications(): Promise<Notification[]> {
  return mockRequest([...notifStore]);
}

// Mark notification as read (local state mutation)
export async function markAsRead(notificationId: string): Promise<void> {
  const idx = notifStore.findIndex(n => n.notification_id === notificationId);
  if (idx !== -1) notifStore[idx] = { ...notifStore[idx], read: true };
  return mockRequest(undefined as unknown as void, 100);
}

// Mark all as read
export async function markAllRead(): Promise<void> {
  notifStore = notifStore.map(n => ({ ...n, read: true }));
  return mockRequest(undefined as unknown as void, 100);
}

export function getUnreadCount(): number {
  return notifStore.filter(n => !n.read).length;
}
