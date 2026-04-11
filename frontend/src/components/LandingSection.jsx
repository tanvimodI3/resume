import React, { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import TypingTitle from './TypingTitle';

function LandingSection() {
  const ref = useRef(null);

  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start start', 'end start'],
  });

  // Title scales up then fades
  const titleScale = useTransform(scrollYProgress, [0, 0.6], [1, 1.15]);
  const titleOpacity = useTransform(scrollYProgress, [0, 0.4, 0.7], [1, 0.6, 0]);

  return (
    <section ref={ref} className="landing-section">
      <motion.div
        style={{ scale: titleScale, opacity: titleOpacity }}
        className="landing-title-wrap"
      >
        <div className="landing-eyebrow">
          <span>AI-Powered Hiring</span>
        </div>

        <TypingTitle />

        <p className="landing-subtitle">
          Resume parsing, candidate scoring,<br />
          and AI interview — all in one place.
        </p>
      </motion.div>

      <div className="landing-scroll-hint">
        <div className="scroll-line" />
        <span>scroll</span>
      </div>
    </section>
  );
}

export default LandingSection;