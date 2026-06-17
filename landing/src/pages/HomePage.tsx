import { Footer } from '../components/layout/Footer';
import { Navbar } from '../components/layout/Navbar';
import { AiTasks } from '../components/sections/AiTasks';
import { Catalog } from '../components/sections/Catalog';
import { Channels } from '../components/sections/Channels';
import { Dashboard } from '../components/sections/Dashboard';
import { Features } from '../components/sections/Features';
import { FinalCta } from '../components/sections/FinalCta';
import { Hero } from '../components/sections/Hero';
import { Philosophy } from '../components/sections/Philosophy';
import { Pilot } from '../components/sections/Pilot';
import { Problem } from '../components/sections/Problem';
import { Scenarios } from '../components/sections/Scenarios';
import { Security } from '../components/sections/Security';
import { Solution } from '../components/sections/Solution';

export function HomePage() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <Problem />
        <Solution />
        <Philosophy />
        <Features />
        <Scenarios />
        <Channels />
        <Catalog />
        <Dashboard />
        <AiTasks />
        <Security />
        <Pilot />
        <FinalCta />
      </main>
      <Footer />
    </>
  );
}
