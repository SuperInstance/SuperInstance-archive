import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { ProvisionItem, ProvisionTransaction } from '@/types';

interface ProvisionsState {
  items: ProvisionItem[];
  transactions: ProvisionTransaction[];
  categories: string[];
  locations: string[];
  shoppingList: string[];
}

const initialState: ProvisionsState = {
  items: [],
  transactions: [],
  categories: [
    'food',
    'beverage',
    'safety',
    'medical',
    'tools',
    'spare_parts',
    'cleaning',
    'personal_care',
    'other'
  ],
  locations: [
    'Galley',
    'Forward Cabin',
    'Aft Cabin',
    'Salon',
    'Engine Room',
    'Deck Box',
    'Refrigerator',
    'Freezer',
    'Emergency Kit',
    'Tool Locker'
  ],
  shoppingList: [],
};

const provisionsSlice = createSlice({
  name: 'provisions',
  initialState,
  reducers: {
    addProvisionItem: (state, action: PayloadAction<Omit<ProvisionItem, 'id' | 'last_updated'>>) => {
      const item: ProvisionItem = {
        id: `provision_${Date.now()}`,
        last_updated: new Date(),
        ...action.payload,
      };
      state.items.push(item);
      
      // Add initial transaction
      const transaction: ProvisionTransaction = {
        id: `transaction_${Date.now()}`,
        item_id: item.id,
        type: 'add',
        quantity: item.quantity,
        timestamp: new Date(),
        notes: 'Initial inventory',
      };
      state.transactions.unshift(transaction);
    },
    
    updateProvisionItem: (state, action: PayloadAction<{ id: string; updates: Partial<ProvisionItem> }>) => {
      const { id, updates } = action.payload;
      const itemIndex = state.items.findIndex(i => i.id === id);
      if (itemIndex !== -1) {
        state.items[itemIndex] = {
          ...state.items[itemIndex],
          ...updates,
          last_updated: new Date(),
        };
      }
    },
    
    updateQuantity: (state, action: PayloadAction<{ itemId: string; quantity: number; type: 'add' | 'remove' | 'consume'; notes?: string }>) => {
      const { itemId, quantity, type, notes } = action.payload;
      const itemIndex = state.items.findIndex(i => i.id === itemId);
      
      if (itemIndex !== -1) {
        const item = state.items[itemIndex];
        let newQuantity = item.quantity;
        
        switch (type) {
          case 'add':
            newQuantity += quantity;
            break;
          case 'remove':
          case 'consume':
            newQuantity = Math.max(0, newQuantity - quantity);
            break;
        }
        
        item.quantity = newQuantity;
        item.last_updated = new Date();
        
        // Add transaction
        const transaction: ProvisionTransaction = {
          id: `transaction_${Date.now()}`,
          item_id: itemId,
          type,
          quantity,
          timestamp: new Date(),
          notes,
        };
        
        state.transactions.unshift(transaction);
        
        // Add to shopping list if low
        if (item.minimum_stock && newQuantity <= item.minimum_stock) {
          if (!state.shoppingList.includes(itemId)) {
            state.shoppingList.push(itemId);
          }
        }
      }
    },
    
    deleteProvisionItem: (state, action: PayloadAction<string>) => {
      const itemId = action.payload;
      state.items = state.items.filter(i => i.id !== itemId);
      state.transactions = state.transactions.filter(t => t.item_id !== itemId);
      state.shoppingList = state.shoppingList.filter(id => id !== itemId);
    },
    
    addToShoppingList: (state, action: PayloadAction<string>) => {
      const itemId = action.payload;
      if (!state.shoppingList.includes(itemId)) {
        state.shoppingList.push(itemId);
      }
    },
    
    removeFromShoppingList: (state, action: PayloadAction<string>) => {
      const itemId = action.payload;
      state.shoppingList = state.shoppingList.filter(id => id !== itemId);
    },
    
    clearShoppingList: (state) => {
      state.shoppingList = [];
    },
    
    addCategory: (state, action: PayloadAction<string>) => {
      const category = action.payload.toLowerCase();
      if (!state.categories.includes(category)) {
        state.categories.push(category);
        state.categories.sort();
      }
    },
    
    addLocation: (state, action: PayloadAction<string>) => {
      if (!state.locations.includes(action.payload)) {
        state.locations.push(action.payload);
        state.locations.sort();
      }
    },
    
    markExpired: (state, action: PayloadAction<{ itemId: string; quantity: number }>) => {
      const { itemId, quantity } = action.payload;
      const itemIndex = state.items.findIndex(i => i.id === itemId);
      
      if (itemIndex !== -1) {
        const item = state.items[itemIndex];
        item.quantity = Math.max(0, item.quantity - quantity);
        item.last_updated = new Date();
        
        // Add expiry transaction
        const transaction: ProvisionTransaction = {
          id: `transaction_${Date.now()}`,
          item_id: itemId,
          type: 'expire',
          quantity,
          timestamp: new Date(),
          notes: 'Item expired',
        };
        
        state.transactions.unshift(transaction);
      }
    },
    
    checkExpiredItems: (state) => {
      const now = new Date();
      const expiredItems: string[] = [];
      
      state.items.forEach(item => {
        if (item.expiry_date && new Date(item.expiry_date) <= now && item.quantity > 0) {
          expiredItems.push(item.id);
        }
      });
      
      return expiredItems;
    },
    
    generateShoppingListFromLowStock: (state) => {
      state.shoppingList = [];
      
      state.items.forEach(item => {
        if (item.minimum_stock && item.quantity <= item.minimum_stock) {
          state.shoppingList.push(item.id);
        }
      });
    },
    
    bulkUpdateQuantities: (state, action: PayloadAction<{ updates: { itemId: string; quantity: number; notes?: string }[] }>) => {
      const { updates } = action.payload;
      const timestamp = new Date();
      
      updates.forEach(update => {
        const itemIndex = state.items.findIndex(i => i.id === update.itemId);
        if (itemIndex !== -1) {
          state.items[itemIndex].quantity = update.quantity;
          state.items[itemIndex].last_updated = timestamp;
          
          // Add transaction
          const transaction: ProvisionTransaction = {
            id: `transaction_${Date.now()}_${update.itemId}`,
            item_id: update.itemId,
            type: 'add',
            quantity: update.quantity,
            timestamp,
            notes: update.notes || 'Bulk update',
          };
          
          state.transactions.unshift(transaction);
        }
      });
    },
    
    clearTransactionHistory: (state, action: PayloadAction<string | undefined>) => {
      if (action.payload) {
        // Clear for specific item
        state.transactions = state.transactions.filter(t => t.item_id !== action.payload);
      } else {
        // Clear all transactions
        state.transactions = [];
      }
    },
  },
});

export const {
  addProvisionItem,
  updateProvisionItem,
  updateQuantity,
  deleteProvisionItem,
  addToShoppingList,
  removeFromShoppingList,
  clearShoppingList,
  addCategory,
  addLocation,
  markExpired,
  checkExpiredItems,
  generateShoppingListFromLowStock,
  bulkUpdateQuantities,
  clearTransactionHistory,
} = provisionsSlice.actions;

export default provisionsSlice.reducer;