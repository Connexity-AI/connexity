import type { UserPublic } from '@/client/types.gen';

export interface Session extends Pick<UserPublic, 'id' | 'email'> {
  isAuth: boolean;
}
