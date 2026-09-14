export const browserNotification = {
  async requestPermission(): Promise<boolean> {
    if (!('Notification' in window)) {
      return false;
    }
    if (Notification.permission === 'granted') {
      return true;
    }
    if (Notification.permission !== 'denied') {
      const permission = await Notification.requestPermission();
      return permission === 'granted';
    }
    return false;
  },

  async notify(title: string, body: string) {
    const hasPermission = await this.requestPermission();
    if (!hasPermission) return;

    try {
      new Notification(title, {
        body,
        icon: '/favicon.ico',
      });
    } catch (err) {
      console.error('Failed to show browser notification:', err);
    }
  },
};
