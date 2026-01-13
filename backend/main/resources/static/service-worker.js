// 서비스 워커 설치 및 활성화
self.addEventListener('install', event => {
  console.log('서비스 워커가 설치되었습니다.');
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  console.log('서비스 워커가 활성화되었습니다.');
  return self.clients.claim();
});

// 푸시 이벤트 처리
self.addEventListener('push', event => {
  console.log('푸시 알림 수신:', event);
  
  let message = '새로운 알림이 있습니다.';
  
  if (event.data) {
    try {
      // 수신된 데이터 확인
      const data = event.data.text();
      console.log('수신된 푸시 데이터:', data);
      message = data;
    } catch (e) {
      console.error('푸시 데이터 파싱 오류:', e);
    }
  }
  
  const options = {
    body: message,
    icon: '/favicon.ico', // 아이콘 경로 (서버에 있는지 확인 필요)
    badge: '/favicon.ico', // 배지 아이콘 경로
    vibrate: [100, 50, 100],
    data: {
      url: '/' // 알림 클릭 시 이동할 URL
    }
  };
  
  event.waitUntil(
    self.registration.showNotification('달그락', options)
  );
});

// 알림 클릭 이벤트 처리
self.addEventListener('notificationclick', event => {
  console.log('알림이 클릭되었습니다:', event);
  event.notification.close();
  
  // 알림 클릭 시 메인 페이지로 이동
  event.waitUntil(
    clients.openWindow(event.notification.data.url || '/')
  );
});