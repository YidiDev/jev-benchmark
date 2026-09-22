"""The 30-question AP World History short-answer exam used by CT10.

Each question has a fixed point value (2-5, summing to exactly 100 across
all 30 -- a realistic non-uniform mix, like real AP exams) and a
**checklist-style rubric**: exactly `points` independent, structurally-
described criteria, one point each. Criteria describe WHAT KIND of content
earns a point (e.g. "identifies the specific empire/dynasty responsible")
without stating the actual correct answer -- that's kept in a separate
`reference_facts` list, used only for (a) generating ground-truth student
answers and (b) the with-answer-key grading condition. This separation is
what makes the without-key condition a genuine test of the grading
model's own historical knowledge rather than a rubric-reading exercise
with the answer secretly embedded in the criteria text.

Point distribution: 5 questions worth 2, 12 worth 3, 11 worth 4, 2 worth
5 -- chosen to sum to exactly 100 while keeping each question's criteria
count matched to how many genuinely distinct, checkable elements a strong
answer to that specific prompt would contain (not an arbitrary RNG
assignment independent of content, since a checklist rubric's length is
inherently tied to what the question is actually asking).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExamQuestion:
    id: str
    prompt: str
    points: int
    criteria: list[str]  # length == points; structural, no answer content
    reference_facts: list[str]  # length == points; the actual correct element per criterion


EXAM_QUESTIONS: list[ExamQuestion] = [
    ExamQuestion(
        "q01",
        "Describe the political and administrative structure the Mongol Empire used to govern its territory.",
        3,
        [
            "Identifies the specific empire and its founding leader.",
            "Describes a specific structural/administrative mechanism used to organize the empire.",
            "Explains how that mechanism enabled control over a vast, ethnically diverse territory.",
        ],
        [
            "The Mongol Empire, founded by Genghis Khan.",
            "A decimal-based military-administrative system organizing people into units of 10, 100, 1,000, and 10,000, cutting across old tribal loyalties.",
            "This let the Mongols rapidly mobilize and command a huge multi-ethnic population without relying on pre-existing tribal/clan hierarchies.",
        ],
    ),
    ExamQuestion(
        "q02",
        "Explain the significance of the Indian Ocean trade network before 1500 CE.",
        4,
        [
            "Identifies specific goods exchanged along the network.",
            "Identifies specific regions or civilizations that participated.",
            "Explains the role of a specific environmental/navigational factor that made the trade possible.",
            "Explains a specific cultural or religious effect of this trade network.",
        ],
        [
            "Goods such as spices, textiles, porcelain, and gold.",
            "East Africa (Swahili coast), Arabia, India, Southeast Asia, and China.",
            "The predictable seasonal reversal of monsoon winds allowed sailors to plan round-trip voyages.",
            "The spread of Islam along the East African coast and Southeast Asia via merchants and travelers.",
        ],
    ),
    ExamQuestion(
        "q03",
        "Describe the circumstances of the fall of the Byzantine Empire in 1453.",
        3,
        [
            "Identifies which power conquered the empire and its capital.",
            "Describes a specific military factor that enabled the conquest.",
            "Explains one broader historical significance of the fall.",
        ],
        [
            "The Ottoman Empire under Mehmed II captured Constantinople.",
            "The Ottomans used massive siege cannons to breach the city's ancient walls.",
            "It marked the end of the Roman imperial line and pushed Ottoman control over key Eastern Mediterranean trade routes, spurring Europeans to seek new routes to Asia.",
        ],
    ),
    ExamQuestion(
        "q04",
        "Explain the impact of the Black Death on European society and economy.",
        3,
        [
            "States the scale of the population impact.",
            "Explains a specific labor-market or economic-system effect.",
            "Explains a specific social or religious effect.",
        ],
        [
            "It killed roughly a third of Europe's population in the mid-14th century.",
            "The resulting labor shortage drove up wages and weakened the manorial/serfdom system, accelerating the decline of feudalism.",
            "It provoked religious crises (including scapegoating of minority groups) and challenges to the Church's authority when prayer failed to stop the disease.",
        ],
    ),
    ExamQuestion(
        "q05",
        "Describe how the Aztec Empire extracted resources from the peoples it conquered.",
        2,
        [
            "Describes the mechanism used to extract resources from subject peoples.",
            "Explains the purpose this mechanism served for the empire.",
        ],
        [
            "A tribute system requiring conquered city-states to regularly deliver goods, labor, or military service.",
            "It funded the imperial capital Tenochtitlan and the elite without requiring direct administration of every conquered territory.",
        ],
    ),
    ExamQuestion(
        "q06",
        "Explain how the Ottoman Empire used the devshirme system.",
        3,
        [
            "Describes the specific practice the term refers to.",
            "Explains what became of those taken through this practice.",
            "Explains the purpose this system served for the empire.",
        ],
        [
            "The periodic levy of Christian boys from Balkan provinces.",
            "They were converted to Islam and trained, often becoming elite Janissary soldiers or high administrators.",
            "It built a loyal military and administrative class personally tied to the Sultan rather than to hereditary nobility.",
        ],
    ),
    ExamQuestion(
        "q07",
        "Explain the significance of the Atlantic Slave Trade for the development of the Americas.",
        5,
        [
            "Describes the trade's basic structure/route.",
            "Identifies the primary form of labor enslaved Africans were forced into.",
            "Explains a specific economic significance to European/colonial powers.",
            "Explains a specific demographic impact on West/Central Africa.",
            "Explains a specific lasting cultural impact on the Americas.",
        ],
        [
            "The triangular trade linked Europe, West Africa, and the Americas, forcibly transporting millions of enslaved Africans across the Atlantic.",
            "Forced labor on plantations producing cash crops such as sugar, tobacco, and cotton.",
            "Plantation exports generated enormous wealth for European trading empires and colonial economies.",
            "It depopulated and destabilized parts of West and Central Africa over several centuries.",
            "It produced lasting African cultural, religious, and linguistic influence across the Americas.",
        ],
    ),
    ExamQuestion(
        "q08",
        "Explain the causes of the Protestant Reformation.",
        3,
        [
            "Identifies a specific triggering event or figure.",
            "Explains a specific grievance with the existing religious institution.",
            "Explains a specific technological or political factor that helped the movement spread.",
        ],
        [
            "Martin Luther's 1517 Ninety-Five Theses criticizing the Church.",
            "Objection to the sale of indulgences and perceived corruption within the Catholic Church.",
            "The printing press allowed Luther's ideas to spread rapidly; some German princes backed reform for political/economic reasons.",
        ],
    ),
    ExamQuestion(
        "q09",
        "Describe the Columbian Exchange and its effects.",
        4,
        [
            "Describes what kinds of things were exchanged across the Atlantic.",
            "Explains a specific effect on indigenous American populations.",
            "Explains a specific economic effect.",
            "Explains a specific demographic or cultural effect on either hemisphere.",
        ],
        [
            "Crops, livestock, people, and diseases were exchanged between the Americas and Afro-Eurasia after 1492.",
            "Old World diseases like smallpox devastated indigenous populations, who had no prior immunity.",
            "New World crops (maize, potatoes) boosted food supplies and population growth in Afro-Eurasia.",
            "European livestock and crops transformed American ecosystems and diets, reshaping societies on both sides.",
        ],
    ),
    ExamQuestion(
        "q10",
        "Explain the significance of the Tokugawa Shogunate's sakoku policy.",
        3,
        [
            "Describes what the policy restricted.",
            "Explains a specific motivation behind the policy.",
            "Identifies a specific exception to the policy's isolation.",
        ],
        [
            "It severely restricted foreign trade and travel, largely closing Japan off from the outside world.",
            "The Shogunate sought to curb the spread of Christianity and limit foreign political/economic influence.",
            "Limited Dutch trade was still permitted through the controlled port of Nagasaki (Dejima).",
        ],
    ),
    ExamQuestion(
        "q11",
        "Explain the causes of the Scientific Revolution in Europe.",
        3,
        [
            "Explains a specific new intellectual method that emerged.",
            "Explains how this challenged an existing source of authority.",
            "Identifies a specific figure or discovery associated with the movement.",
        ],
        [
            "New emphasis on empirical observation and experimentation as a basis for knowledge.",
            "This challenged reliance on classical texts (Aristotle) and religious doctrine as the sole sources of truth.",
            "Figures such as Copernicus, Galileo, or Newton and discoveries like heliocentrism.",
        ],
    ),
    ExamQuestion(
        "q12",
        "Explain how Enlightenment political philosophy influenced later revolutions.",
        4,
        [
            "Identifies a specific Enlightenment political concept.",
            "Identifies a specific thinker associated with that concept.",
            "Explains its influence on one specific revolution.",
            "Explains its influence on a second specific revolution.",
        ],
        [
            "Concepts of natural rights, the social contract, and separation of powers.",
            "Thinkers such as Locke, Rousseau, or Montesquieu.",
            "These ideas directly informed the American Revolution's arguments for self-government.",
            "They also directly informed the French Revolution's calls for liberty, equality, and the end of absolute monarchy.",
        ],
    ),
    ExamQuestion(
        "q13",
        "Describe the causes and effects of the French Revolution.",
        5,
        [
            "Explains a specific financial/economic cause.",
            "Explains a specific social/political cause tied to the existing social order.",
            "Explains the influence of a specific set of ideas on the revolution.",
            "Describes a specific major effect on the French political system.",
            "Describes a specific broader/longer-term effect.",
        ],
        [
            "Chronic government debt and a fiscal crisis worsened by costly wars.",
            "Resentment of the rigid estates system and privileges enjoyed by the nobility and clergy.",
            "Enlightenment ideas about liberty, equality, and popular sovereignty.",
            "The monarchy was overthrown and Louis XVI was eventually executed.",
            "The instability that followed eventually enabled Napoleon Bonaparte's rise to power.",
        ],
    ),
    ExamQuestion(
        "q14",
        "Explain the significance of the Haitian Revolution.",
        4,
        [
            "Identifies a specific leader associated with the revolution.",
            "Describes what made the revolution historically unprecedented.",
            "Explains a specific effect on the French colonial empire.",
            "Explains a specific broader influence on other abolition/independence movements.",
        ],
        [
            "Toussaint Louverture led the enslaved population's uprising.",
            "It was the only successful large-scale slave revolt that led to the founding of an independent nation (Haiti).",
            "France lost its most profitable colony, weakening its position in the Americas.",
            "It inspired enslaved and colonized peoples elsewhere and alarmed slaveholding powers.",
        ],
    ),
    ExamQuestion(
        "q15",
        "Explain the process of industrialization in Britain.",
        4,
        [
            "Identifies a specific key technological innovation.",
            "Describes a specific change in how production was organized.",
            "Explains a specific resource advantage Britain had.",
            "Explains a specific social effect of industrialization.",
        ],
        [
            "The steam engine, which powered machinery and later railways/ships.",
            "The shift from home-based cottage industry to centralized factories.",
            "Abundant domestic coal and iron deposits.",
            "Rapid urbanization as workers moved to industrial cities, often under harsh conditions.",
        ],
    ),
    ExamQuestion(
        "q16",
        "Explain the causes of European imperialism in Africa in the late 19th century.",
        4,
        [
            "Explains a specific economic motivation.",
            "Explains a specific political/competitive motivation among European powers.",
            "Explains a specific ideological justification used.",
            "Explains a specific technological factor that enabled conquest.",
        ],
        [
            "The desire for raw materials and new markets to fuel industrial economies.",
            "Competition and prestige rivalry among European powers, formalized at events like the Berlin Conference.",
            "Social Darwinist and racial ideologies used to justify domination as a 'civilizing mission'.",
            "Military technology such as the Maxim gun gave Europeans a decisive advantage.",
        ],
    ),
    ExamQuestion(
        "q17",
        "Describe the effects of the Opium Wars on China.",
        3,
        [
            "Identifies the trade dispute that triggered the conflict.",
            "Describes the military outcome.",
            "Explains a specific consequence for Chinese sovereignty.",
        ],
        [
            "Britain's opium trade with China and China's attempts to suppress it.",
            "China was militarily defeated by Britain (and later other powers).",
            "China was forced to sign unequal treaties (e.g. the Treaty of Nanjing), ceding Hong Kong and opening treaty ports to foreign control.",
        ],
    ),
    ExamQuestion(
        "q18",
        "Explain the significance of the Meiji Restoration in Japan.",
        3,
        [
            "Describes the political change that occurred.",
            "Describes a specific area of rapid modernization that followed.",
            "Explains the broader outcome for Japan's international standing.",
        ],
        [
            "The Tokugawa Shogunate was ended and imperial rule was formally restored.",
            "Japan rapidly modernized its military, industry, and government institutions along Western models.",
            "Japan became a major industrial and military power, avoiding colonization and later projecting its own imperial power.",
        ],
    ),
    ExamQuestion(
        "q19",
        "Explain the causes of World War I.",
        4,
        [
            "Explains the role of the alliance system.",
            "Explains the role of imperial/nationalist competition among powers.",
            "Identifies the specific triggering event.",
            "Explains the role of militarization/arms buildup.",
        ],
        [
            "A web of alliances meant a conflict between two powers could rapidly draw in the rest of Europe.",
            "Competing nationalist and imperial ambitions created ongoing tension among the great powers.",
            "The assassination of Archduke Franz Ferdinand in Sarajevo in 1914.",
            "A prewar arms race, including naval competition between Britain and Germany, heightened readiness for war.",
        ],
    ),
    ExamQuestion(
        "q20",
        "Explain the significance of the Bolshevik Revolution.",
        4,
        [
            "Identifies the leader/party that seized power.",
            "Describes what government structure was overthrown or replaced.",
            "Explains a specific policy change that followed.",
            "Explains a specific broader global significance.",
        ],
        [
            "Vladimir Lenin and the Bolshevik Party seized power in 1917.",
            "They overthrew the provisional government that had replaced the Tsar earlier that year.",
            "Russia withdrew from World War I and began building a Communist state.",
            "It created the world's first major Communist state, inspiring and alarming movements worldwide.",
        ],
    ),
    ExamQuestion(
        "q21",
        "Describe the causes and consequences of the Great Depression.",
        4,
        [
            "Identifies the specific triggering economic event.",
            "Explains why the crisis spread globally.",
            "Explains a specific social/economic consequence.",
            "Explains a specific political consequence.",
        ],
        [
            "The 1929 U.S. stock market crash.",
            "Interconnected global trade and lending meant the crisis spread rapidly to other economies.",
            "Mass unemployment and severe hardship worldwide.",
            "Economic desperation contributed to the rise of authoritarian and fascist movements in several countries.",
        ],
    ),
    ExamQuestion(
        "q22",
        "Explain the causes of World War II in Europe.",
        4,
        [
            "Explains the connection to the outcome of the previous world war.",
            "Explains the rise of a specific expansionist regime.",
            "Explains the role of a specific diplomatic policy by other powers.",
            "Identifies the specific triggering event.",
        ],
        [
            "Resentment over the terms of the Treaty of Versailles fueled German nationalism.",
            "The rise of Hitler and Nazi ideology pursuing territorial expansion.",
            "Western powers' policy of appeasement failed to stop escalating German aggression.",
            "Germany's invasion of Poland in 1939 triggered declarations of war.",
        ],
    ),
    ExamQuestion(
        "q23",
        "Describe the process of decolonization in Africa after World War II.",
        3,
        [
            "Explains a specific factor that weakened European colonial powers after the war.",
            "Explains a specific driver of African independence movements.",
            "States the general timeframe/pattern of independence across the continent.",
        ],
        [
            "European powers were economically and militarily weakened by the war, undermining their ability to hold colonies.",
            "Rising nationalist movements and leaders across Africa organized for self-rule.",
            "Most African nations gained independence in a wave concentrated mainly in the 1950s-1960s.",
        ],
    ),
    ExamQuestion(
        "q24",
        "Explain the significance of the Non-Aligned Movement during the Cold War.",
        2,
        [
            "Describes what stance member countries took relative to the two Cold War blocs.",
            "Identifies a specific leader or country associated with the movement.",
        ],
        [
            "Member states sought to avoid formally aligning with either the U.S.-led or Soviet-led bloc.",
            "Figures such as Jawaharlal Nehru (India), Gamal Abdel Nasser (Egypt), or Josip Broz Tito (Yugoslavia).",
        ],
    ),
    ExamQuestion(
        "q25",
        "Explain the causes of the Chinese Communist Revolution.",
        3,
        [
            "Identifies the two main competing factions.",
            "Explains a specific source of popular support for the Communists.",
            "Explains how the Japanese invasion affected the balance of power.",
        ],
        [
            "The Chinese Communist Party under Mao Zedong and the Nationalist (Guomindang) government under Chiang Kai-shek.",
            "Communist promises of land reform appealed to the rural peasantry.",
            "The Japanese invasion during WWII significantly weakened the Nationalist government, benefiting the Communists.",
        ],
    ),
    ExamQuestion(
        "q26",
        "Explain the significance of the Green Revolution in the 20th century.",
        2,
        [
            "Describes the specific agricultural change involved.",
            "Explains its effect on global food supply.",
        ],
        [
            "The development and spread of high-yield crop varieties and modern agricultural techniques.",
            "It substantially increased food production, especially in developing nations, reducing famine risk.",
        ],
    ),
    ExamQuestion(
        "q27",
        "Describe the causes and effects of the fall of the Soviet Union.",
        4,
        [
            "Explains a specific underlying economic weakness.",
            "Identifies a specific reform policy/leader associated with the collapse.",
            "Explains a specific political factor within the Soviet republics.",
            "States the broader global effect of the collapse.",
        ],
        [
            "Long-term economic stagnation and inefficiency in the centrally planned economy.",
            "Mikhail Gorbachev's policies of glasnost (openness) and perestroika (restructuring).",
            "Rising nationalist movements within Soviet republics pushed for independence.",
            "It ended the Cold War and the bipolar global power structure.",
        ],
    ),
    ExamQuestion(
        "q28",
        "Explain the significance of the Rwandan Genocide.",
        2,
        [
            "Identifies the two ethnic groups involved in the conflict.",
            "States a key fact about the international community's response.",
        ],
        [
            "Ethnic conflict between the Hutu majority and Tutsi minority in 1994.",
            "The international community largely failed to intervene despite the scale of the mass killing.",
        ],
    ),
    ExamQuestion(
        "q29",
        "Describe the effects of globalization on the world economy since 1990.",
        3,
        [
            "Explains a specific effect on international trade or economic interdependence.",
            "Explains a specific effect enabled by communication/technology.",
            "Explains a specific cultural consequence or backlash.",
        ],
        [
            "Trade barriers fell and supply chains became increasingly interconnected across countries.",
            "Advances in digital communication accelerated the flow of capital, information, and business across borders.",
            "Increased cultural exchange has also provoked backlash and movements defending local/national identity.",
        ],
    ),
    ExamQuestion(
        "q30",
        "Explain the significance of the Arab Spring.",
        2,
        [
            "States the general nature and starting period of the uprisings.",
            "Identifies a specific factor that helped the movement spread.",
        ],
        [
            "A wave of pro-democracy protests and uprisings against authoritarian governments beginning around 2010-2011.",
            "Social media helped organize protests and spread information rapidly across the region.",
        ],
    ),
]

TOTAL_POINTS = sum(q.points for q in EXAM_QUESTIONS)
assert TOTAL_POINTS == 100, f"exam must sum to 100 points, got {TOTAL_POINTS}"
assert len(EXAM_QUESTIONS) == 30, f"exam must have 30 questions, got {len(EXAM_QUESTIONS)}"

EXAM_BY_ID = {q.id: q for q in EXAM_QUESTIONS}

for _q in EXAM_QUESTIONS:
    assert len(_q.criteria) == _q.points, f"{_q.id}: {len(_q.criteria)} criteria != {_q.points} points"
    assert len(_q.reference_facts) == _q.points, f"{_q.id}: {len(_q.reference_facts)} facts != {_q.points} points"
