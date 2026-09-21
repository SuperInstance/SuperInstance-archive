import { useSpring } from '@react-spring/web';
import { useState, useCallback, useRef } from 'react';

export interface GestureConfig {
  swipeThreshold: number;
  longPressDelay: number;
  doubleTapInterval: number;
  pinchSensitivity: number;
  enabled: boolean;
}

export interface SwipeDirection {
  direction: 'left' | 'right' | 'up' | 'down';
  velocity: number;
  distance: number;
}

export interface GestureHandlers {
  onSwipe?: (direction: SwipeDirection) => void;
  onLongPress?: (position: { x: number; y: number }) => void;
  onDoubleTap?: (position: { x: number; y: number }) => void;
  onPinch?: (scale: number, origin: { x: number; y: number }) => void;
  onTap?: (position: { x: number; y: number }) => void;
}

const defaultConfig: GestureConfig = {
  swipeThreshold: 50,
  longPressDelay: 500,
  doubleTapInterval: 300,
  pinchSensitivity: 0.1,
  enabled: true,
};

export const useGestures = (
  handlers: GestureHandlers = {},
  config: Partial<GestureConfig> = {}
) => {
  const finalConfig = { ...defaultConfig, ...config };
  const [isLongPressing, setIsLongPressing] = useState(false);
  const lastTapRef = useRef<number>(0);
  const longPressTimeoutRef = useRef<NodeJS.Timeout>();
  const swipeStartRef = useRef<{ x: number; y: number; time: number } | null>(null);

  // Spring for visual feedback
  const [{ scale, opacity }, api] = useSpring(() => ({
    scale: 1,
    opacity: 1,
    config: { tension: 300, friction: 30 },
  }));

  // Clear long press timeout
  const clearLongPressTimeout = useCallback(() => {
    if (longPressTimeoutRef.current) {
      clearTimeout(longPressTimeoutRef.current);
      longPressTimeoutRef.current = undefined;
    }
  }, []);

  // Handle swipe detection
  const detectSwipe = useCallback((
    startX: number,
    startY: number,
    endX: number,
    endY: number,
    startTime: number,
    endTime: number
  ) => {
    const deltaX = endX - startX;
    const deltaY = endY - startY;
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
    const velocity = distance / (endTime - startTime);

    if (distance < finalConfig.swipeThreshold) return null;

    let direction: SwipeDirection['direction'];
    
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      direction = deltaX > 0 ? 'right' : 'left';
    } else {
      direction = deltaY > 0 ? 'down' : 'up';
    }

    return { direction, velocity, distance };
  }, [finalConfig.swipeThreshold]);

  // Simple gesture handlers
  const bind = () => ({
    onMouseDown: (event: React.MouseEvent) => {
      if (!finalConfig.enabled) return;
      
      const { clientX: x, clientY: y } = event;
      swipeStartRef.current = { x, y, time: Date.now() };
      
      if (handlers.onLongPress) {
        longPressTimeoutRef.current = setTimeout(() => {
          setIsLongPressing(true);
          handlers.onLongPress?.({ x, y });
          api.start({ scale: 1.05, opacity: 0.8 });
        }, finalConfig.longPressDelay);
      }
      
      api.start({ scale: 0.98, opacity: 0.9 });
    },
    
    onMouseUp: (event: React.MouseEvent) => {
      if (!finalConfig.enabled) return;
      
      const { clientX: x, clientY: y } = event;
      const currentTime = Date.now();
      
      clearLongPressTimeout();
      setIsLongPressing(false);
      api.start({ scale: 1, opacity: 1 });
      
      // Handle tap
      const timeSinceLastTap = currentTime - lastTapRef.current;
      if (timeSinceLastTap < finalConfig.doubleTapInterval) {
        handlers.onDoubleTap?.({ x, y });
      } else {
        setTimeout(() => {
          if (Date.now() - lastTapRef.current >= finalConfig.doubleTapInterval) {
            handlers.onTap?.({ x, y });
          }
        }, finalConfig.doubleTapInterval);
      }
      lastTapRef.current = currentTime;
      
      // Detect swipe
      if (swipeStartRef.current && handlers.onSwipe) {
        const swipe = detectSwipe(
          swipeStartRef.current.x,
          swipeStartRef.current.y,
          x,
          y,
          swipeStartRef.current.time,
          currentTime
        );

        if (swipe) {
          handlers.onSwipe(swipe);
        }
      }
      
      swipeStartRef.current = null;
    },
    
    onTouchStart: (event: React.TouchEvent) => {
      if (!finalConfig.enabled) return;
      
      const touch = event.touches[0];
      const { clientX: x, clientY: y } = touch;
      swipeStartRef.current = { x, y, time: Date.now() };
      
      if (handlers.onLongPress) {
        longPressTimeoutRef.current = setTimeout(() => {
          setIsLongPressing(true);
          handlers.onLongPress?.({ x, y });
          api.start({ scale: 1.05, opacity: 0.8 });
        }, finalConfig.longPressDelay);
      }
      
      api.start({ scale: 0.98, opacity: 0.9 });
    },
    
    onTouchEnd: (event: React.TouchEvent) => {
      if (!finalConfig.enabled) return;
      
      const touch = event.changedTouches[0];
      const { clientX: x, clientY: y } = touch;
      const currentTime = Date.now();
      
      clearLongPressTimeout();
      setIsLongPressing(false);
      api.start({ scale: 1, opacity: 1 });
      
      // Handle tap
      const timeSinceLastTap = currentTime - lastTapRef.current;
      if (timeSinceLastTap < finalConfig.doubleTapInterval) {
        handlers.onDoubleTap?.({ x, y });
      } else {
        setTimeout(() => {
          if (Date.now() - lastTapRef.current >= finalConfig.doubleTapInterval) {
            handlers.onTap?.({ x, y });
          }
        }, finalConfig.doubleTapInterval);
      }
      lastTapRef.current = currentTime;
      
      // Detect swipe
      if (swipeStartRef.current && handlers.onSwipe) {
        const swipe = detectSwipe(
          swipeStartRef.current.x,
          swipeStartRef.current.y,
          x,
          y,
          swipeStartRef.current.time,
          currentTime
        );

        if (swipe) {
          handlers.onSwipe(swipe);
        }
      }
      
      swipeStartRef.current = null;
    },

    onWheel: (event: WheelEvent) => {
      if (!finalConfig.enabled || !handlers.onPinch) return;

      if (event.ctrlKey || event.metaKey) {
        event.preventDefault();
        
        const scale = 1 - event.deltaY * finalConfig.pinchSensitivity * 0.01;
        const rect = (event.target as Element)?.getBoundingClientRect();
        
        if (rect) {
          const origin = {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
          };
          
          handlers.onPinch(scale, origin);
        }
      }
    },
  });

  return {
    bind,
    gesturing: isLongPressing,
    springs: { scale, opacity },
    api,
  };
};

export default useGestures;