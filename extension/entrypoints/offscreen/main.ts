import type { InspectRequest } from '@/utils/analysis';
import { inspect } from '@/utils/inspect';

browser.runtime.onMessage.addListener((message: InspectRequest) => {
  if (message.type === 'inspect') return Promise.resolve(inspect(message));
});
