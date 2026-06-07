import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { PropsWithChildren } from 'react';
import { useQuery } from '@tanstack/react-query';

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
  const [selectedShopId, setSelectedShopIdState] = useState(() => localStorage.getItem(SHOP_STORAGE_KEY) ?? '');

  const shopsQuery = useQuery({
    queryKey: queryKeys.shops,
    queryFn: () => apiClient.listShops(),
  });

  const shops = shopsQuery.data ?? [];

  useEffect(() => {
    if (shops.length === 0) {
      return;
    }
    const exists = shops.some((shop) => shop.id === selectedShopId);
    if (!selectedShopId || !exists) {
      setSelectedShopIdState(shops[0].id);
    }
  }, [shops, selectedShopId]);

  const setSelectedShopId = useCallback((shopId: string) => {
    setSelectedShopIdState(shopId);
    if (shopId) {
      localStorage.setItem(SHOP_STORAGE_KEY, shopId);
    } else {
      localStorage.removeItem(SHOP_STORAGE_KEY);
    }
  }, []);

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
      isLoading: shopsQuery.isLoading,
      error: shopsQuery.error instanceof Error ? shopsQuery.error.message : null,
    }),
    [shops, selectedShopId, selectedShop, setSelectedShopId, shopsQuery.isLoading, shopsQuery.error],
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
