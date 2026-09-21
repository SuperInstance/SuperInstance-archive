import { configureStore } from '@reduxjs/toolkit';
import { persistStore, persistReducer } from 'redux-persist';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { combineReducers } from 'redux';

import instrumentsReducer from './slices/instrumentsSlice';
import fishLogReducer from './slices/fishLogSlice';
import anchorWatchReducer from './slices/anchorWatchSlice';
import emergencyReducer from './slices/emergencySlice';
import crewTasksReducer from './slices/crewTasksSlice';
import maintenanceReducer from './slices/maintenanceSlice';
import tanksReducer from './slices/tanksSlice';
import provisionsReducer from './slices/provisionsSlice';
import remoteDesktopReducer from './slices/remoteDesktopSlice';
import voiceReducer from './slices/voiceSlice';
import settingsReducer from './slices/settingsSlice';

const persistConfig = {
  key: 'root',
  storage: AsyncStorage,
  whitelist: [
    'fishLog',
    'anchorWatch',
    'emergency',
    'crewTasks',
    'maintenance',
    'tanks',
    'provisions',
    'settings'
  ],
};

const rootReducer = combineReducers({
  instruments: instrumentsReducer,
  fishLog: fishLogReducer,
  anchorWatch: anchorWatchReducer,
  emergency: emergencyReducer,
  crewTasks: crewTasksReducer,
  maintenance: maintenanceReducer,
  tanks: tanksReducer,
  provisions: provisionsReducer,
  remoteDesktop: remoteDesktopReducer,
  voice: voiceReducer,
  settings: settingsReducer,
});

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
      },
    }),
});

export const persistor = persistStore(store);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;