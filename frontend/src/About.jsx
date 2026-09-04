import './About.css'

function About() {
  return (
    <main className="about-page">
      <nav className="about-nav">
        <div className="about-brand">
          <span className="about-brand-logo">P</span>
          <span>PaperScope</span>
        </div>

        <div className="about-nav-links">
          <a href="/">Home</a>
          <a href="/about" className="active">About Us</a>
          <button onClick={() => (window.location.href = '/login')}>
            Get Started
          </button>
        </div>
      </nav>

      <section className="about-hero">
        <p className="about-eyebrow">ABOUT PAPERSCOPE</p>
        <h1>
          <span className="about-heading-red">Building a more</span>
          <br />
          <span>intelligent learning ecosystem.</span>
        </h1>
        <p className="about-lead">
          PaperScope is an AI-enabled learning intelligence platform designed
          to identify competency gaps, personalize learning, and strengthen
          capability through intelligent assessment.
        </p>
      </section>

      <section className="about-content">

        <article className="about-block">
          <span className="about-number">01</span>
          <div>
            <h2>Our Aim</h2>
            <p>
              PaperScope aims to transform learning from a one-size-fits-all
              experience into an intelligent, competency-driven journey.
            </p>
            <p>
              Our goal is to help learners understand where they stand,
              identify what needs improvement, and receive personalized
              pathways to strengthen their capabilities.
            </p>
          </div>
        </article>

        <article className="about-block">
          <span className="about-number">02</span>
          <div>
            <h2>What We Solve</h2>
            <p>
              Conventional learning systems can make it difficult to identify
              individual competency gaps and determine what a learner should
              study next.
            </p>
            <p>
              PaperScope addresses this challenge by connecting assessment,
              competency analysis, learning recommendations, and continuous
              improvement within a unified platform.
            </p>
          </div>
        </article>

        <article className="about-block">
          <span className="about-number">03</span>
          <div>
            <h2>Our Solution</h2>
            <p>
              PaperScope uses AI-driven learning intelligence to turn learning
              materials and assessment data into actionable insights.
            </p>

            <ul>
              <li>Identify competency gaps through intelligent assessment.</li>
              <li>Analyze learning materials and question papers.</li>
              <li>Generate quizzes and MCQs from uploaded content.</li>
              <li>Recommend personalized learning pathways.</li>
              <li>Track learning progress and assessment performance.</li>
            </ul>
          </div>
        </article>

        <article className="about-block">
          <span className="about-number">04</span>
          <div>
            <h2>Our SIH Mission</h2>
            <p>
              PaperScope is developed in response to the Smart India Hackathon
              2026 problem statement from the Ministry of Statistics &
              Programme Implementation (MoSPI).
            </p>
            <p>
              Our vision is to contribute towards an AI-enabled learning
              platform that identifies competency gaps, recommends personalized
              training, integrates with the iGOT Karmayogi ecosystem, and
              generates quizzes and MCQs from learning materials.
            </p>
          </div>
        </article>

      </section>

      <footer className="about-footer">
        <div className="about-footer-main">
          <div className="about-quote">
            <span>“</span>
            <p>
              Education is not the filling of a pail,
              <br />
              but the lighting of a fire.
              <span className="quote-end">”</span>
            </p>
          </div>

          <div className="about-contact">
            <span>CONTACT US</span>
            <a href="mailto:contact@paperscope.in">
              contact@paperscope.in
            </a>
          </div>
        </div>

        <div className="about-sih">
          PAPERSCOPE — AN AI-POWERED LEARNING INNOVATION · SMART INDIA
          HACKATHON 2026
        </div>
      </footer>
    </main>
  )
}

export default About
