import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { PropsWithChildren } from 'react';
import { useQuery } from '@tanstack/react-query';

import { useAuth } from './AuthContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { Shop } from '../types/shop';

const SHOP_STORAGE_KEY = 'dm_assistant_selected_shop_id';

interface ShopContextValue {
  shops: Shop[];
  selectedShopId: string;
  selectedShop: Shop | null;
  setSelectedShopId: (shopId: string) => void;
  isLoading: boolean;
  error: string | null;
}

const ShopContext = createContext<ShopContextValue | null>(null);

export function ShopProvider({ children }: PropsWithChildren) {
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const [selectedShopId, setSelectedShopIdState] = useState(() => localStorage.getItem(SHOP_STORAGE_KEY) ?? '');

  const shopsQuery = useQuery({
    queryKey: queryKeys.shops,
    queryFn: () => apiClient.listShops(),
    enabled: isAuthenticated && !isAuthLoading,
  });

  const shops = isAuthenticated ? (shopsQuery.data ?? []) : [];

  const setSelectedShopId = useCallback((shopId: string) => {
    setSelectedShopIdState(shopId);
    if (shopId) {
      localStorage.setItem(SHOP_STORAGE_KEY, shopId);
    } else {
      localStorage.removeItem(SHOP_STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      setSelectedShopIdState('');
      localStorage.removeItem(SHOP_STORAGE_KEY);
      return;
    }

    if (shops.length === 0) {
      return;
    }
    const exists = shops.some((shop) => shop.id === selectedShopId);
    if (!selectedShopId || !exists) {
      setSelectedShopId(shops[0].id);
    }
  }, [isAuthenticated, shops, selectedShopId, setSelectedShopId]);

  const selectedShop = useMemo(
    () => shops.find((shop) => shop.id === selectedShopId) ?? null,
    [shops, selectedShopId],
  );

  const value = useMemo(
    () => ({
      shops,
      selectedShopId,
      selectedShop,
      setSelectedShopId,
      isLoading: isAuthLoading || (isAuthenticated && shopsQuery.isPending),
      error: shopsQuery.error instanceof Error ? shopsQuery.error.message : null,
    }),
    [
      shops,
      selectedShopId,
      selectedShop,
      setSelectedShopId,
      isAuthLoading,
      isAuthenticated,
      shopsQuery.isPending,
      shopsQuery.error,
    ],
  );

  return <ShopContext.Provider value={value}>{children}</ShopContext.Provider>;
}

export function useShop() {
  const context = useContext(ShopContext);
  if (!context) {
    throw new Error('useShop must be used within ShopProvider');
  }
  return context;
}
