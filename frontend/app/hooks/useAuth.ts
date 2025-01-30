'use client';

import { useContext } from 'react';
import { AuthContext } from '@app/context/auth-context';
import type { AuthContextType } from '@app/types/auth';

export function useAuth(): AuthContextType {
  return useContext(AuthContext);
}
