import React, { useState, useEffect, useRef } from 'react';

const FULL_TEXT = 'forreal.';
const TYPE_DELAY = 110;
const DELETE_DELAY = 70;
const PAUSE_FULL = 2200;
const PAUSE_EMPTY = 500;

function TypingTitle() {
  const [displayed, setDisplayed] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    function tick() {
      if (!isDeleting) {
        if (displayed.length < FULL_TEXT.length) {
          setDisplayed(FULL_TEXT.slice(0, displayed.length + 1));
          timerRef.current = setTimeout(tick, TYPE_DELAY);
        } else {
          timerRef.current = setTimeout(() => {
            setIsDeleting(true);
          }, PAUSE_FULL);
        }
      } else {
        if (displayed.length > 0) {
          setDisplayed(displayed.slice(0, -1));
          timerRef.current = setTimeout(tick, DELETE_DELAY);
        } else {
          timerRef.current = setTimeout(() => {
            setIsDeleting(false);
          }, PAUSE_EMPTY);
        }
      }
    }

    timerRef.current = setTimeout(tick, isDeleting ? DELETE_DELAY : TYPE_DELAY);
    return () => clearTimeout(timerRef.current);
  }, [displayed, isDeleting]);

  return (
    <h1 className="typing-title" aria-label={FULL_TEXT}>
      <span>{displayed}</span>
      <span className="typing-cursor" aria-hidden="true" />
    </h1>
  );
}

export default TypingTitle;