'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@app/hooks/useAuth';
import type { CopertineResponse } from '@app/types/copertine';

interface UseCopertineParams {
  offset: number;
  limit: number;
}

interface UseCopertineResult {
  data: CopertineResponse | null;
  error: string | null;
  isLoading: boolean;
}

export function useCopertine({ offset, limit }: UseCopertineParams): UseCopertineResult {
  const [data, setData] = useState<CopertineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { token } = useAuth();

  useEffect(() => {
    const fetchData = async () => {
      console.log('[useCopertine] Starting fetch with token:', !!token);
      
      if (!token) {
        console.log('[useCopertine] No token available');
        setError('Authentication required');
        setIsLoading(false);
        return;
      }

      try {
        console.log('[useCopertine] Fetching data:', { offset, limit });
        setIsLoading(true);
        setError(null);

        const response = await fetch(`/api/copertine?offset=${offset}&limit=${limit}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json',
          },
          credentials: 'include',
        });
        
        console.log('[useCopertine] Response status:', response.status);
        
        if (!response.ok) {
          const errorData = await response.json();
          console.error('[useCopertine] Error response:', errorData);
          throw new Error(errorData.detail || errorData.error || 'Failed to fetch data');
        }

        const jsonData = await response.json();
        console.log('[useCopertine] Data received:', jsonData);
        setData(jsonData);
      } catch (err) {
        console.error('Error fetching copertine:', err);
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [offset, limit, token]);

  return { data, error, isLoading };
}
