# Mice Humanoid Robot Thesis: Master Engineering Reference & Formulas Catalog
## คู่มือรวบรวมสมการวิศวกรรม สถาปัตยกรรมระบบ และงานวิจัยอ้างอิงฉบับสมบูรณ์

> **Overview**: This master document contains the complete engineering formulas, algorithms, physical models, and verified academic references supporting the Mice Humanoid Robot thesis. It spans 72 architectural equation cards and 138 peer-reviewed bibliography sources (covering both premier international foundational literature and nationwide Thai research universities).

## Table of Contents
1. [Executive Summary (บทสรุปผู้บริหาร)](#1-executive-summary)
2. [Nationwide Thai Research & University Bibliography](#2-nationwide-thai-research--university-bibliography)
3. [International Classical & Foundational Bibliography](#3-international-classical--foundational-bibliography)
4. [Master Equation Catalog (72 Cards)](#4-master-equation-catalog)
5. [BibTeX Quick Reference](#5-bibtex-quick-reference)

---
## 1. Executive Summary

เอกสารฉบับนี้รวบรวมสมการทางคณิตศาสตร์ โมเดลจลนศาสตร์ (Kinematics) พลศาสตร์ (Dynamics) การควบคุมมอเตอร์และ PID ระบบการมองเห็นและการรู้จำใบหน้า ตลอดจนโมเดลการประมวลผลเสียงพูด (ASR/TTS) และภาษาไทย ที่ใช้จริงและเป็นพื้นฐานทางทฤษฎีในหุ่นยนต์ Mice ทั้ง 72 หัวข้อ โดยเชื่อมโยงกับงานวิจัยที่ผ่านการ peer-review จากทั้งสถาบันอุดมศึกษาชั้นนำทั่วทุกภูมิภาคของประเทศไทย (32 รายการ) และงานวิจัยระดับสากลที่เป็นรากฐานสำคัญ (106 รายการ)

---
## 2. Nationwide Thai Research & University Bibliography

| No. | Institution | Authors & Year | Title | Supporting Scope | Verified DOI / Link |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [105] | Chulalongkorn University | P. Uthong and V. Sangveraphunsiri (2015) | **Dexterity Measure for a 2-DOF Revolute Spherical Serial Manipulator** | Laboratory of Robotics and Automation (LRP), จุฬาลงกรณ์มหาวิทยาลัย (Chulalongkorn University). Evaluates Jacobian matrix conditioning, manipulability measure, and kinematic singularity avoidance for revolute joint arm mechanisms. Directly supports DLS damping and singular-pose regularized IK. | [10.4028/www.scientific.net/amm.799-800.1016](https://doi.org/10.4028/www.scientific.net/amm.799-800.1016) |
| [106] | Chulalongkorn University | P. Kantithammakorn, P. Punyabukkana, and P. N. Pratanwanich (2022) | **Using Automatic Speech Recognition to Assess Thai Speech Language Fluency in the Montreal Cognitive Assessment (MoCA)** | ภาควิชาวิศวกรรมคอมพิวเตอร์ จุฬาลงกรณ์มหาวิทยาลัย (Chulalongkorn University). Investigates Thai acoustic modeling, syllable segmentation, and Word Error Rate (WER) evaluation in real-world spoken interactions with background noise. | [10.3390/s22041583](https://doi.org/10.3390/s22041583) |
| [107] | Chulalongkorn University | P. Prakrankamanant (2021) | **Data augmentation for Thai natural language processing using different tokenization** | ภาควิชาวิศวกรรมคอมพิวเตอร์ จุฬาลงกรณ์มหาวิทยาลัย (Chulalongkorn University CUIR). Analyzes unsegmented Thai script word-boundary tokenization, dictionary maximal matching vs deep learning segmentation, and mathematical impact on Thai WER/CER reproducibility. | [10.58837/chula.the.2021.98](https://doi.org/10.58837/chula.the.2021.98) |
| [108] | KMUTT FIBO | H. Wongsuwarn and D. Laowattana (2006) | **Experimental Study for a FIBO Humanoid Robot** | สถาบันวิทยาการหุ่นยนต์ภาคสนาม มจธ. (KMUTT FIBO). วิเคราะห์จลนศาสตร์ข้อต่อและแรงบิดยึดจับ (joint holding torque) tau = sum(r_i x m_i g) รวมถึงการโก่งตัวภายใต้โหลดพลศาสตร์ สำหรับหุ่นยนต์ฮิวแมนนอยด์ (Formulates link kinematics, joint holding torques tau = sum(r_i x m_i g), and structural deflection under dynamic loads for a physical humanoid robot developed in Thailand). | [10.1109/ramech.2006.252690](https://doi.org/10.1109/ramech.2006.252690) |
| [109] | KMUTT | S. Malakar, W. Chiracharit, K. Chamnongthai, and T. Charoenpong (2021) | **Masked Face Recognition Using Principal component analysis and Deep learning** | ภาควิชาวิศวกรรมอิเล็กทรอนิกส์และโทรคมนาคม มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าธนบุรี มจธ. (KMUTT). Evaluates feature embedding distances, cosine similarity metrics, and demographic/occlusion error rates (FMR/FNMR) under real Thai camera benchmarks. | [10.1109/ecti-con51831.2021.9454857](https://doi.org/10.1109/ecti-con51831.2021.9454857) |
| [110] | KMITL | S. Panaudomsup, T. Subhagandha, K. Chanma, and S. Boksuwan (2025) | **Developing HERMS Temperature Control: A Study on PID-P and PI-P Cascade Control** | ภาควิชาวิศวกรรมการวัดและควบคุม สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง สจล. (KMITL). Practical implementation of discrete-time PID anti-windup clamping and derivative filtering on embedded microcontrollers to avoid actuator saturation. | [10.1109/ecti-con64996.2025.11101691](https://doi.org/10.1109/ecti-con64996.2025.11101691) |
| [111] | Chiang Mai University | N. Theera-Umpon, S. Chansareewittaya, and S. Auephanwiriyakul (2011) | **Phoneme and tonal accent recognition for Thai speech** | ศูนย์วิศวกรรมชีวการแพทย์ และภาควิชาวิศวกรรมไฟฟ้า มหาวิทยาลัยเชียงใหม่ มช. (Chiang Mai University CMU). Analyzes acoustic feature parameters (MFCC, spectral envelopes, fundamental frequency F_0) and tonal classification for Thai spoken language; establishes 16 kHz sampling and framing requirements. | [10.1016/j.eswa.2011.04.142](https://doi.org/10.1016/j.eswa.2011.04.142) |
| [112] | Chiang Mai University | S. Auephanwiriyakul, S. Phitakwinai, and W. Suttapak (2013) | **Thai sign language translation using Scale Invariant Feature Transform and Hidden Markov Models** | ภาควิชาวิศวกรรมคอมพิวเตอร์ มหาวิทยาลัยเชียงใหม่ มช. (Chiang Mai University CMU). Real-time visual feature tracking, frame segmentation, and temporal state modeling on camera-based embedded systems with latency constraints. | [10.1016/j.patrec.2013.04.017](https://doi.org/10.1016/j.patrec.2013.04.017) |
| [113] | Conference paper (Chulalongkorn University | P. Bamrungthai and V. Sangveraphunsiri (2013) | **A Multi-Camera System for Mobile Robot Localization and Calibration** | Laboratory of Robotics and Automation (LRP), จุฬาลงกรณ์มหาวิทยาลัย (Chulalongkorn University). Multi-camera intrinsic/extrinsic calibration, pinhole projection geometry, and lens distortion correction for accurate spatial tracking. | [10.2316/p.2013.799-107](https://doi.org/10.2316/p.2013.799-107) |
| [114] | Chulalongkorn University | CUIR / Chulalongkorn University (2023) | **Thai language sentiment analysis with a hybrid method on WangchanBERTa-CNN-BiLSTM** | จุฬาลงกรณ์มหาวิทยาลัย (Chulalongkorn University). Evaluates Transformer-based language representation (WangchanBERTa), subword tokenization, and vector cosine similarity for Thai semantic intent classification and intent matching. | [10.58837/chula.the.2023.1363](https://doi.org/10.58837/chula.the.2023.1363) |
| [115] | Chulalongkorn University | V. Sangveraphunsiri and K. Chooprasird (2010) | **Dynamics and control of a 5-DOF manipulator based on an H-4 parallel mechanism** | Laboratory of Robotics and Automation (LRP), จุฬาลงกรณ์มหาวิทยาลัย (Chulalongkorn University). สร้างสมการการเคลื่อนที่พลศาสตร์และแรงบิดข้อต่อแขนกลหุ่นยนต์ tau = M(q)q_ddot + C(q,q_dot)q_dot + G(q) ด้วยวิธีลากรานจ์และนิวตัน-ออยเลอร์ รวมพจน์แรงเสียดทานและขีดจำกัดแรงบิดแอคชูเอเตอร์เซอร์โว (Derives multi-link rigid-body equations of motion tau = M(q)q_ddot + C(q,q_dot)q_dot + G(q) using Lagrange-Euler and Newton-Euler methods, including joint friction and actuator torque limits for robotic arms). | [10.1007/s00170-010-2722-3](https://doi.org/10.1007/s00170-010-2722-3) |
| [116] | KMUTNB | A. Suebsomran, N. Manoch, and P. Kwanthong (2022) | **Development and Control of a Lower Limb Exoskeleton Robot** | Department of Teacher Training in Mechanical Engineering, มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าพระนครเหนือ มจพ. (KMUTNB). วิเคราะห์จลนศาสตร์ข้อต่อ แรงบิดต้านทานแรงโน้มถ่วง tau = sum(r_i x m_i g) และการควบคุมมอเตอร์ขับเคลื่อนเซอร์โวข้อต่อภายใต้ภาระโหลดแปรผัน (Analyzes link kinematics, gravitational holding torques tau = sum(r_i x m_i g), and DC motor actuator control under varying payload). | [10.1109/iceccme55909.2022.9988414](https://doi.org/10.1109/iceccme55909.2022.9988414) |
| [117] | IEEE / SICE Conference paper (Thammasat University SIIT | M. Hayashi, Y. Koide, K. Matsuhara, S. Ushida, H. Oku, and W. Kongprawechnon (2017) | **Adaptive modeling and compliance control for RC servo motor** | สถาบันเทคโนโลยีนานาชาติสิรินธร มหาวิทยาลัยธรรมศาสตร์ (SIIT Thammasat University). การสร้างแบบจำลองไฟฟ้า-กลศาสตร์ของ RC เซอร์โวมอเตอร์ และการควบคุมความยืดหยุ่นจำยอม (compliance control) ตลอดจนการประมาณค่าพารามิเตอร์แบบปรับตัวสำหรับการควบคุมตำแหน่งและแรงบิด (Adaptive electromechanical parameter identification and compliance control for hobby RC servo motors). | [10.23919/sice.2017.8105557](https://doi.org/10.23919/sice.2017.8105557) |
| [118] | Book chapter / Springer (NECTEC / NSTDA | C. Wutiwiwatchai, V. Chunwijitra, S. Chunwijitra, P. Sertsi, S. Kasuriya, P. Chootrakool, and K. Thangthai (2018) | **The NECTEC 2015 Thai Open-Domain Automatic Speech Recognition System** | ศูนย์เทคโนโลยีอิเล็กทรอนิกส์และคอมพิวเตอร์แห่งชาติ สวทช. (NECTEC / NSTDA). สถาปัตยกรรมระบบรู้จำเสียงพูดภาษาไทยมาตรฐานแห่งชาติ การสร้างแบบจำลองเสียงระดับพยางค์ (syllable acoustic modeling) โครงสร้างหน่วยเสียง และการประเมินอัตราความผิดพลาดระดับคำ (Word Error Rate: WER) ภายใต้สำเนียงและสัญญาณรบกวน (National open-domain Thai ASR architecture, syllable acoustic modeling, and WER benchmarking). | [10.1007/978-3-319-70016-8_11](https://doi.org/10.1007/978-3-319-70016-8_11) |
| [119] | Mahidol University BART LAB | S. Nakdhamabhorn, M. B. Pillai, and J. Suthakorn (2021) | **Design and development of sensorless based 5-DOF bilaterally controlled surgical manipulator: A prototype** | ศูนย์เครือข่ายวิจัยเทคโนโลยีหุ่นยนต์ชีวการแพทย์ คณะวิศวกรรมศาสตร์ มหาวิทยาลัยมหิดล (BART LAB Mahidol University). การวิเคราะห์จลนศาสตร์ไปข้างหน้าและจลนศาสตร์ผกผัน (Forward/Inverse Kinematics) ตารางพารามิเตอร์ D-H และการควบคุมแรงบิดข้อต่อแบบสองทิศทางสำหรับแขนกล 5-DOF (Multi-link D-H kinematics, Jacobian transformations, and bilateral joint control for articulated serial manipulators). | [10.11591/eei.v10i2.2331](https://doi.org/10.11591/eei.v10i2.2331) |
| [120] | VISTEC & Kasetsart & Chulalongkorn | W. Phatthiyaphaibun, C. Chaksangchaichot, T. Rakthammanon, E. Chuangsuwanich, and S. Nutanong (2023) | **Crowdsourced Data Validation for ASR Training** | ความร่วมมือระหว่าง สถาบันวิทยสิริเมธี (VISTEC), มหาวิทยาลัยเกษตรศาสตร์ (KU), และ จุฬาลงกรณ์มหาวิทยาลัย (ผู้พัฒนา PyThaiNLP). การตรวจสอบความถูกต้องของคลังข้อมูลเสียงพูดภาษาไทย การปรับมาตรฐานข้อความ (text normalization) และการฝึกสอนโมเดลเสียงเพื่อลดอัตราความผิดพลาด WER สำหรับโมเดลการรู้จำเสียงพูดภาษาไทยสมัยใหม่ (Validates Thai speech datasets, transcription normalization, and acoustic modeling quality to minimize WER in modern Thai ASR). | [10.21437/interspeech.2023-389](https://doi.org/10.21437/interspeech.2023-389) |
| [121] | Mahidol University BART LAB | R. Phuengsuk and J. Suthakorn (2016) | **A study on risk assessment for improving reliability of rescue robots** | ศูนย์เครือข่ายวิจัยเทคโนโลยีหุ่นยนต์ชีวการแพทย์ คณะวิศวกรรมศาสตร์ มหาวิทยาลัยมหิดล (BART LAB Mahidol University). ระเบียบวิธีประเมินความเสี่ยง (Risk assessment), การระบุอันตรายจากจุดหนีบและการหยุดเคลื่อนที่ฉุกเฉินตามมาตรฐานความปลอดภัยหุ่นยนต์ (Hazard identification, failure mode analysis, and emergency stop risk mitigation under robot safety standards). | [10.1109/robio.2016.7866399](https://doi.org/10.1109/robio.2016.7866399) |
| [122] | Suranaree University of Technology | J. Srisertpol and C. Khajorntraidet (2009) | **Estimation of DC motor variable torque using adaptive compensation** | สาขาวิชาวิศวกรรมเมคคาทรอนิกส์ มหาวิทยาลัยเทคโนโลยีสุรนารี มทส. (SUT Mechatronics). แบบจำลองคณิตศาสตร์ของมอเตอร์กระแสตรง การประมาณค่าแรงบิดภาระทางกลที่แปรผัน และการชดเชยแรงบิดแบบปรับตัวสำหรับการควบคุมข้อต่อเซอร์โว (Mathematical modeling of DC motor variable mechanical load torques, back-EMF estimation, and adaptive torque compensation). | [10.1109/ccdc.2009.5191882](https://doi.org/10.1109/ccdc.2009.5191882) |
| [123] | Asian Institute of Technology / AIT | N. Ajjanaromvat and M. Parnichkun (2018) | **Trajectory tracking using online learning LQR with adaptive learning control of a leg-exoskeleton for disorder gait rehabilitation** | สถาบันเทคโนโลยีแห่งเอเชีย AIT (Asian Institute of Technology, Thailand). การวางแผนเส้นทางการเคลื่อนที่ข้อต่อหุ่นยนต์ การควบคุมการเคลื่อนที่ตามวิถีโค้งเรียบ (smooth trajectory tracking) และสมการพลศาสตร์การป้อนกลับแรงบิดเพื่อลดความคลาดเคลื่อนเชิงตำแหน่งและความเร็ว (Articulated joint trajectory tracking, smooth position/velocity profiling, error state equations, and adaptive torque feedback). | [10.1016/j.mechatronics.2018.03.003](https://doi.org/10.1016/j.mechatronics.2018.03.003) |
| [124] | NECTEC VAJA TTS | C. Wutiwiwatchai, A. Thangthai, A. Chotimongkol, C. Hansakunbuntheung, and N. Thatphithakkul (2011) | **Accent level adjustment in bilingual Thai-English text-to-speech synthesis** | ศูนย์เทคโนโลยีอิเล็กทรอนิกส์และคอมพิวเตอร์แห่งชาติ สวทช. (NECTEC / NSTDA - VAJA TTS). การสังเคราะห์เสียงพูดสองภาษาไทย-อังกฤษ (Bilingual Thai-English Text-to-Speech) การปรับระดับความสูงต่ำของเสียง (pitch contour) การคำนวณระยะเวลาหน่วยเสียง และการแคชไฟล์เสียง WAV เพื่อลดความหน่วง (Bilingual Thai-English speech synthesis, prosodic tone modeling, phonetic duration calculation, and audio WAV caching). | [10.1109/asru.2011.6163947](https://doi.org/10.1109/asru.2011.6163947) |
| [125] | National Institute of Metrology, Thailand | K. Nontapot and C. Nutsathaporn (2023) | **Uncertainty reduction of CO2 laser calibration system in National Institute of Metrology (Thailand)** | สถาบันมาตรวิทยาแห่งชาติ มว. (National Institute of Metrology, Thailand - NIMT). การวิเคราะห์ความไม่แน่นอนของการวัดแบบ Type A และ Type B การกระจายความแปรปรวนแบบผลรวม (combined uncertainty propagation) และงบประมาณความไม่แน่นอนในการสอบเทียบอุปกรณ์ตามมาตรฐาน GUM (Type A and Type B measurement uncertainty analysis, combined variance propagation, and calibration fitting under the international GUM framework). | [10.1117/12.2671699](https://doi.org/10.1117/12.2671699) |
| [126] | Prince of Songkla University | N. Kongchoo, P. Santiprapan, and N. Jindapetch (2022) | **Mathematical Model and PI Controller Design Based on Indirect Vector Control for Permanent Magnet Synchronous Motor** | ภาควิชาวิศวกรรมไฟฟ้า มหาวิทยาลัยสงขลานครินทร์ ม.อ. (Prince of Songkla University PSU). การสร้างแบบจำลองสมการสถานะกลศาสตร์ไฟฟ้าของมอเตอร์ การปรับจูนเกนตัวควบคุม PI แบบไม่ต่อเนื่อง การป้องกันการอิ่มตัวของตัวสะสมอินทิกรัล (anti-windup clamping) และการควบคุมแรงบิดสถานะคงตัว (Mathematical motor state equations, discrete PI controller gain tuning, anti-windup clamping, and steady-state holding torque control). | [10.37936/ecti-cit.2022163.245351](https://doi.org/10.37936/ecti-cit.2022163.245351) |
| [127] | Khon Kaen University | J. Chaichawananit and S. Saiyod (2016) | **Solving inverse kinematics problem of robot arm based on a-star algorithm** | ภาควิชาวิทยาการคอมพิวเตอร์ คณะวิทยาศาสตร์ มหาวิทยาลัยขอนแก่น มข. (Khon Kaen University KKU). การแก้ปัญหาจลนศาสตร์ผกผัน (Inverse Kinematics) สำหรับแขนกลหุ่นยนต์ การแปลงพิกัดคาร์ทีเซียนสู่มุมข้อต่อ และการค้นหาเส้นทางการเคลื่อนที่ที่หลีกเลี่ยงการชน (Formulates robotic arm inverse kinematics, Cartesian-to-joint angle transformations, and singularity/collision-free trajectory optimization). | [10.1109/jcsse.2016.7748846](https://doi.org/10.1109/jcsse.2016.7748846) |
| [128] | Khon Kaen University | J. Klangkankullapun, P. Seresangtakul, and P. Janyoi (2025) | **Thai Elderly Speech Recognition Using Transfer Learning** | ห้องปฏิบัติการวิจัยการประมวลผลภาษาธรรมชาติและเสียงพูด วิทยาลัยการคอมพิวเตอร์ มหาวิทยาลัยขอนแก่น มข. (Khon Kaen University KKU). การประยุกต์ใช้การเรียนรู้ถ่ายโอน (transfer learning) ในระบบการรู้จำเสียงพูดภาษาไทย การปรับแบบจำลองเสียง (acoustic model adaptation) และการวัดประสิทธิภาพอัตราความผิดพลาดระดับคำ WER (Applies acoustic transfer learning and domain adaptation to improve Thai ASR accuracy and evaluate Word Error Rate). | [10.1109/icsec67360.2025.11298001](https://doi.org/10.1109/icsec67360.2025.11298001) |
| [129] | Journal paper / IEEE Access (Burapha University | R. Khoeun, W. Yookwan, P. Chophuk, A. Rodtook, and K. Chinnasarn (2023) | **Emotion Recognition of Partial Face Using Star-Like Particle Polygon Estimation** | คณะวิทยาการสารสนเทศ มหาวิทยาลัยบูรพา มบ. (Faculty of Informatics, Burapha University BUU). การสกัดจุดสำคัญบนใบหน้าและการจำแนกใบหน้าภายใต้การบดบังบางส่วน (partial face occlusion) โดยใช้รูปหลายเหลี่ยมอนุภาค และการวัดระยะเวกเตอร์คุณลักษณะของใบหน้า (Facial landmark extraction, partial occlusion robustness, and geometric embedding distance evaluation). | [10.1109/access.2023.3305514](https://doi.org/10.1109/access.2023.3305514) |
| [130] | Burapha University | U. Suttapakti and A. Bunpeng (2021) | **Adaptive Kernel Transform for Face Recognition Under Uneven Illumination Conditions** | คณะวิทยาการสารสนเทศ มหาวิทยาลัยบูรพา มบ. (Faculty of Informatics, Burapha University BUU). การปรับแก้ภาพใบหน้าภายใต้สภาพแสงไม่สม่ำเสมอ การแปลงเคอร์เนลแบบปรับตัวเพื่อรักษาระยะเวกเตอร์ใบหน้า และการลดผลกระทบของการเปลี่ยนแปลงความสว่างของกล้อง (Evaluates adaptive kernel transforms for face recognition under uneven illumination and variable camera exposure). | [10.1109/icsec53205.2021.9684605](https://doi.org/10.1109/icsec53205.2021.9684605) |
| [131] | Prince of Songkla University | P. Neranon and R. Bicker (2016) | **Force/position control of a robot manipulator for human-robot interaction** | ภาควิชาวิศวกรรมเครื่องกล คณะวิศวกรรมศาสตร์ มหาวิทยาลัยสงขลานครินทร์ ม.อ. (Prince of Songkla University PSU). การควบคุมแรงและตำแหน่งของแขนกลหุ่นยนต์สำหรับการปฏิสัมพันธ์ระหว่างมนุษย์กับหุ่นยนต์ จลนศาสตร์เมทริกซ์จาโคเบียน (Jacobian matrix) และการจำกัดแรงกระทำเพื่อความปลอดภัยในการเคลื่อนไหว (Formulates manipulator kinematics, Jacobian matrix mapping, contact force control, and safe compliance limits for physical human-robot interaction). | [10.2298/tsci151005036n](https://doi.org/10.2298/tsci151005036n) |
| [132] | Naresuan University | P. Nattharith and M. Güzel (2016) | **Machine vision and fuzzy logic-based navigation control of a goal-oriented mobile robot** | ภาควิชาวิศวกรรมไฟฟ้าและคอมพิวเตอร์ คณะวิศวกรรมศาสตร์ มหาวิทยาลัยนเรศวร มน. (Naresuan University NU). การประมวลผลภาพจากกล้องแบบเวลาจริง การแปลงพิกัดภาพสู่ระนาบอ้างอิง และการควบคุมการเคลื่อนที่ตามเป้าหมายภายใต้ข้อจำกัดความหน่วงของกล้อง (Real-time camera frame processing, coordinate transformations, and visual tracking control under frame latency constraints). | [10.1177/1059712316645845](https://doi.org/10.1177/1059712316645845) |
| [133] | RMUTT Mechatronics | P. Sutyasadi, M. Wicaksono, and D. Maneetham (2023) | **Improvement Control of a Three Axis Articulated Robotic Arm Using PID Cascade Control** | ภาควิชาวิศวกรรมเมคคาทรอนิกส์ มหาวิทยาลัยเทคโนโลยีราชมงคลธัญบุรี มทร.ธัญบุรี (RMUTT Mechatronics). การควบคุมตำแหน่งแขนกล 3 แกนด้วยตัวควบคุม PID แบบคาสเคด การจัดการแรงบิดข้อต่อ และการชดเชยการอิ่มตัวของแอคชูเอเตอร์ (Articulated robotic arm joint position and torque control using discrete cascade PID loops and anti-windup saturation limits). | [10.1109/citsm60085.2023.10455548](https://doi.org/10.1109/citsm60085.2023.10455548) |
| [134] | RMUTT Mechatronics | L. Villaverde, D. Maneetham, and T. Rabgyal (2022) | **Camera Calibration Algorithm for Industrial Robot** | ภาควิชาวิศวกรรมเมคคาทรอนิกส์ มหาวิทยาลัยเทคโนโลยีราชมงคลธัญบุรี มทร.ธัญบุรี (RMUTT Mechatronics). อัลกอริทึมการสอบเทียบกล้องสำหรับหุ่นยนต์ การคำนวณพารามิเตอร์ภายในและภายนอก (intrinsic/extrinsic calibration) และการแปลงพิกัดภาพสู่ระบบพิกัดหุ่นยนต์ (Camera calibration algorithm for robotics, intrinsic/extrinsic parameter estimation, lens distortion correction, and camera-to-robot coordinate frame transformations). | [10.1109/itis57155.2022.10009991](https://doi.org/10.1109/itis57155.2022.10009991) |
| [135] | Srinakharinwirot University | K. Grerkiat and V. Rattawut (2023) | **Applying Self-Assessment Manikin (SAM) to Evaluate the Emotional Responses to the Service Robot Feature** | ภาควิชาวิศวกรรมอุตสาหการ คณะวิศวกรรมศาสตร์ มหาวิทยาลัยศรีนครินทรวิโรฒ มศว (Srinakharinwirot University SWU). การประเมินการตอบสนองเชิงพฤติกรรมและการปฏิสัมพันธ์ระหว่างมนุษย์กับหุ่นยนต์บริการ (HRI) ปัจจัยการออกแบบระบบตอบรับด้วยเสียงและการเคลื่อนไหวที่เป็นมิตรและปลอดภัย (Evaluates human-robot interaction ergonomics, emotional user response, and voice/motion service robot design factors). | [10.1109/icbir57571.2023.10147577](https://doi.org/10.1109/icbir57571.2023.10147577) |
| [136] | Walailak University | N. Otanasap and P. Boonbrahm (2017) | **Pre-impact fall detection system using dynamic threshold and 3D bounding box** | สำนักวิชาสารสนเทศศาสตร์ มหาวิทยาลัยวลัยลักษณ์ มวล. (School of Informatics, Walailak University WU). การตรวจจับวัตถุและติดตามเชิงพื้นที่ด้วยกล้อง การสร้างกรอบขอบเขต 3 มิติ (3D bounding box) การกำหนดขีดเริ่มเปลี่ยนแบบปรับตัว (dynamic thresholding) และการลดสัญญาณรบกวนในภาพ (Camera-based 3D bounding box estimation, dynamic thresholding, and real-time spatial motion detection). | [10.1117/12.2266822](https://doi.org/10.1117/12.2266822) |

---
## 3. International Classical & Foundational Bibliography

| No. | Key | Authors & Year | Title | Field / Scope | Verified DOI / Link |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [1] | `robotics` | K. M. Lynch and F. C. Park (2017) | **Modern Robotics: Mechanics, Planning, and Control** | Rigid transforms, Jacobians, gearing and time scaling. The project constants and physical dimensions require separate measurements. | [Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/) |
| [2] | `buss` | S. R. Buss (2009) | **Introduction to Inverse Kinematics with Jacobian Transpose, Pseudoinverse and Damped Least Squares Methods** | Jacobian-based numerical IK. This is an author technical report, not a peer-reviewed journal article. | [Link](https://math.ucsd.edu/~sbuss/ResearchWeb/ikmethods/iksurvey.pdf) |
| [3] | `wampler` | C. W. Wampler (1986) | **Manipulator Inverse Kinematic Solutions Based on Vector Formulations and Damped Least-Squares Methods** | Primary DLS reference; supports regularization near singular configurations, not this robot’s tuning constants. | [10.1109/TSMC.1986.289285](https://doi.org/10.1109/TSMC.1986.289285) |
| [4] | `dh` | J. Denavit and R. S. Hartenberg (1955) | **A Kinematic Notation for Lower-Pair Mechanisms Based on Matrices** | Related matrix-kinematics notation. Do not claim the Three.js hierarchy implements a DH table without deriving one. | [10.1115/1.4011045](https://doi.org/10.1115/1.4011045) |
| [5] | `feedback` | K. J. Åström and R. M. Murray (2008) | **Feedback Systems: An Introduction for Scientists and Engineers** | Feedback models, PID and actuator saturation. Project gains and deadbands still need tuning evidence. | [Link](https://authors.library.caltech.edu/records/yzs24-xsx88) |
| [6] | `gear` | KHK Gears (n.d.) | **Calculation of Gear Dimensions** | Module, tooth count and pitch geometry; supports d = mz and linear travel at the pitch circle. | [Link](https://khkgears.net/new/gear_knowledge/gear_technical_reference/calculation_gear_dimensions.html) |
| [7] | `iso53` | ISO (1998) | **ISO 53:1998 — Cylindrical gears for general and heavy engineering — Standard basic rack tooth profile** | Basic rack tooth profile; does not certify the printed gears or define their measured backlash. | [Link](https://www.iso.org/standard/22643.html) |
| [8] | `dsp` | S. W. Smith (n.d.) | **The Scientist and Engineer’s Guide to Digital Signal Processing: Single Pole Recursive Filters** | First-order recursive low-pass filter and exponential coefficient; use normalized versus Hz frequency consistently. | [Link](https://www.dspguide.com/ch19/2.htm) |
| [9] | `si` | BIPM (2019) | **The International System of Units (SI), SI Brochure** | Radians, seconds and dimensional consistency. Record the exact brochure revision used in the submitted thesis. | [Link](https://www.bipm.org/en/publications/si-brochure) |
| [10] | `rs485` | T. Kugelstadt (2021) | **The RS-485 Design Guide** | Electrical layer, topology, termination, common-mode limits and failsafe biasing; not the Mice application protocol. | [Link](https://www.ti.com/lit/an/slla272d/slla272d.pdf) |
| [11] | `max485` | Maxim Integrated / Analog Devices (n.d.) | **MAX1487–MAX491: Low-Power, Slew-Rate-Limited RS-485/RS-422 Transceivers** | Driver/receiver enables, supply and signal limits. Verify the exact fitted transceiver, not a module vendor’s generic name. | [Link](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX1487-MAX491.pdf) |
| [12] | `esp32` | Espressif Systems (n.d.) | **ESP32 Series Datasheet** | MCU limits and peripheral availability; board-specific wiring and operating measurements remain project evidence. | [Link](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf) |
| [13] | `uart` | Espressif Systems (v4.4.7) | **ESP-IDF Programming Guide: Universal Asynchronous Receiver/Transmitter (UART)** | Frame format, baud configuration and direction control. Versioned background; verify the installed Arduino/IDF versions. | [Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/peripherals/uart.html) |
| [14] | `ledc` | Espressif Systems (v4.4.7) | **ESP-IDF Programming Guide: LED Control (LEDC)** | PWM timing/resolution; does not establish a universal servo pulse range. | [Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/peripherals/ledc.html) |
| [15] | `wifi` | Espressif Systems (v4.4.7) | **ESP-IDF Programming Guide: Wi-Fi** | Implementation basis for scanning and reconnecting; -78/-67 dBm and 12 dB margin are project choices. | [Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/network/esp_wifi.html) |
| [16] | `servo` | Tower Pro (n.d.) | **MG90S** | Manufacturer values for this product only; cannot establish clone behavior or all configured travel and pulse endpoints. | [Link](https://towerpro.com.tw/product/mg90s-3/) |
| [17] | `servo-lib` | ESP32Servo contributors (n.d.) | **ESP32Servo** | Software pulse-generation interface. Cite the installed tag/commit in the final experimental configuration. | [Link](https://github.com/madhephaestus/ESP32Servo) |
| [18] | `encoder` | PJRC (n.d.) | **Encoder Library** | Explains edge counts; distinguish channel cycles, decoded counts and gearbox output turns. | [Link](https://www.pjrc.com/teensy/td_libs_Encoder.html) |
| [19] | `http` | R. Fielding, M. Nottingham and J. Reschke, Eds. (2022) | **HTTP Semantics** | Hub/module API semantics; using HTTP alone does not imply authentication or encryption. | [10.17487/RFC9110](https://www.rfc-editor.org/rfc/rfc9110.html) |
| [20] | `ws` | I. Fette and A. Melnikov (2011) | **The WebSocket Protocol** | Persistent face-event feed, client masking, ping/pong and close handling. | [10.17487/RFC6455](https://www.rfc-editor.org/rfc/rfc6455.html) |
| [21] | `mdns` | S. Cheshire and M. Krochmal (2013) | **Multicast DNS** | Local-link name discovery; inspect the actual mDNS versus scan fallback paths. | [10.17487/RFC6762](https://www.rfc-editor.org/rfc/rfc6762.html) |
| [22] | `dnssd` | S. Cheshire and M. Krochmal (2013) | **DNS-Based Service Discovery** | Service advertisement/discovery background; not proof that every Mice discovery path uses DNS-SD. | [10.17487/RFC6763](https://www.rfc-editor.org/rfc/rfc6763.html) |
| [23] | `json` | T. Bray, Ed. (2017) | **The JavaScript Object Notation (JSON) Data Interchange Format** | Registry and API interchange syntax; project schemas are separate contracts. | [10.17487/RFC8259](https://www.rfc-editor.org/rfc/rfc8259.html) |
| [24] | `base64` | S. Josefsson (2006) | **The Base16, Base32, and Base64 Data Encodings** | Base64 transfer expansion and padding; encoding is not encryption. | [10.17487/RFC4648](https://www.rfc-editor.org/rfc/rfc4648.html) |
| [25] | `md5-security` | S. Turner and L. Chen (2011) | **Updated Security Considerations for the MD5 Message-Digest and the HMAC-MD5 Algorithms** | Explains why an MD5 firmware checksum is not a digital signature or protection against malicious image substitution. | [10.17487/RFC6151](https://www.rfc-editor.org/rfc/rfc6151.html) |
| [26] | `pbkdf` | K. Moriarty, B. Kaliski and A. Rusch (2017) | **PKCS #5: Password-Based Cryptography Specification Version 2.1** | PBKDF2 definition. The hub uses PBKDF2-HMAC-SHA256; firmware UserStore instead stores password strings in NVS. Keep these components distinct. | [10.17487/RFC8018](https://www.rfc-editor.org/rfc/rfc8018.html) |
| [27] | `i2s` | NXP Semiconductors (2022) | **I2S bus specification** | Digital audio framing; distinguish PCM bits, I2S clocking and analog audio input. | [Link](https://www.nxp.com/docs/en/user-manual/UM11732.pdf) |
| [28] | `max98357` | Maxim Integrated / Analog Devices (n.d.) | **MAX98357A/MAX98357B: Tiny, Low-Cost, PCM Class D Amplifier with Class AB Performance** | Digital I2S/PCM amplifier connection; exact ratings depend on device, voltage and load. | [Link](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf) |
| [29] | `tpa3118` | Texas Instruments (n.d.) | **TPA3118D2: 30-W stereo, 60-W mono, 4.5-V to 26-V supply, analog-input Class-D audio amplifier** | Analog-input amplifier, not a direct I2S receiver. Check the actual module input circuit. | [Link](https://www.ti.com/product/TPA3118D2) |
| [30] | `audio-lib` | E. F. Philhower III and contributors (n.d.) | **ESP8266Audio** | Decoder/output architecture and software delta-sigma output. Bench audio quality is not supplied by the library documentation. | [Link](https://github.com/earlephilhower/ESP8266Audio) |
| [31] | `camera-driver` | Espressif Systems (n.d.) | **esp32-camera** | Camera driver, pin mapping and buffering; verify exact board and sensor before citing a pinout. | [Link](https://github.com/espressif/esp32-camera) |
| [32] | `whisper` | A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey and I. Sutskever (2022) | **Robust Speech Recognition via Large-Scale Weak Supervision** | Speech-to-text model basis. Paper results do not establish Thai recognition accuracy or latency on the Mice PC. | [Link](https://arxiv.org/abs/2212.04356) |
| [33] | `faster-whisper` | SYSTRAN and contributors (n.d.) | **faster-whisper: Faster Whisper transcription with CTranslate2** | Actual STT backend imported by Voice; installed package and successful model load require runtime verification. | [Link](https://github.com/SYSTRAN/faster-whisper) |
| [34] | `transformers` | T. Wolf et al. (2020) | **Transformers: State-of-the-Art Natural Language Processing** | Tokenizer/model software framework used in Voice; not a citation for the architecture of every loaded checkpoint. | [10.18653/v1/2020.emnlp-demos.6](https://aclanthology.org/2020.emnlp-demos.6/) |
| [35] | `pytorch` | A. Paszke et al. (2019) | **PyTorch: An Imperative Style, High-Performance Deep Learning Library** | Tensor and inference framework used by the local model; package presence does not prove GPU acceleration. | [Link](https://arxiv.org/abs/1912.01703) |
| [36] | `qwen` | Qwen Team (2026) | **Qwen3.5-4B model card** | Configured default local model. Record checkpoint revision, quantization and actual hardware; loading may be unavailable. | [Link](https://huggingface.co/Qwen/Qwen3.5-4B) |
| [37] | `qlora` | T. Dettmers, A. Pagnoni, A. Holtzman and L. Zettlemoyer (2023) | **QLoRA: Efficient Finetuning of Quantized LLMs** | NF4/double-quantization background for BitsAndBytesConfig. Mice uses quantized inference; no fine-tuning is established. | [Link](https://arxiv.org/abs/2305.14314) |
| [38] | `difflib` | Python Software Foundation (n.d.) | **difflib — Helpers for computing deltas** | Exact saved-answer matching implementation: ratio 2M/T. This is not cosine similarity or a calibrated probability. | [Link](https://docs.python.org/3/library/difflib.html) |
| [39] | `sctk` | National Institute of Standards and Technology (n.d.) | **Speech Recognition Scoring Toolkit (SCTK)** | WER evaluation framework; define Thai segmentation and normalization before comparing recognizers. | [Link](https://github.com/usnistgov/SCTK) |
| [40] | `facenet` | F. Schroff, D. Kalenichenko and J. Philbin (2015) | **FaceNet: A Unified Embedding for Face Recognition and Clustering** | Embedding distances and triplet loss background. The separate recognition application must be inspected before claiming this model is used. | [Link](https://arxiv.org/abs/1503.03832) |
| [41] | `arcface` | J. Deng, J. Guo, N. Xue and S. Zafeiriou (2019) | **ArcFace: Additive Angular Margin Loss for Deep Face Recognition** | Angular-margin embedding literature; does not establish the model or threshold deployed by the external service. | [Link](https://arxiv.org/abs/1801.07698) |
| [42] | `retinaface` | J. Deng, J. Guo, Y. Zhou, J. Yu, I. Kotsia and S. Zafeiriou (2019) | **RetinaFace: Single-stage Dense Face Localisation in the Wild** | Detection and landmarks background. Keep face detection separate from identity recognition. | [Link](https://arxiv.org/abs/1905.00641) |
| [43] | `opencv` | OpenCV contributors (4.13.0) | **Camera Calibration and 3D Reconstruction** | Projection/calibration formulas for camera evaluation; calibration is not established in Mice camera streaming. | [Link](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html) |
| [44] | `zhang` | Z. Zhang (2000) | **A Flexible New Technique for Camera Calibration** | Planar calibration reference for a future calibrated camera experiment. | [10.1109/34.888718](https://doi.org/10.1109/34.888718) |
| [45] | `insightface` | InsightFace contributors (n.d.) | **InsightFace: 2D and 3D Face Analysis** | Related implementation candidate; code license and pretrained-weight permissions are distinct. Not verified as the external app backend. | [Link](https://github.com/deepinsight/insightface) |
| [46] | `wcag` | W3C (2023) | **Web Content Accessibility Guidelines (WCAG) 2.2** | UI evaluation framework; no claim of whole-product conformance without a criterion-by-criterion audit. | [Link](https://www.w3.org/TR/WCAG22/) |
| [47] | `capture` | W3C (n.d.) | **Media Capture and Streams** | Browser microphone acquisition and termination; API availability depends on browser and secure-context rules. | [Link](https://www.w3.org/TR/mediacapture-streams/) |
| [48] | `record` | W3C (n.d.) | **MediaStream Recording** | Push-to-talk recording and chunked input; chunking alone does not make end-to-end speech recognition streaming. | [Link](https://www.w3.org/TR/mediastream-recording/) |
| [49] | `speech` | Web Speech API Community Group (n.d.) | **Web Speech API** | Related browser TTS interface, not the specification for the Windows System.Speech backend used by Voice. | [Link](https://webaudio.github.io/web-speech-api/) |
| [50] | `nvs` | Espressif Systems (v4.4.7) | **ESP-IDF Programming Guide: Non-volatile storage library** | Persistent board identity/settings; storage capability does not imply that stored password values are hashed. | [Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/storage/nvs_flash.html) |
| [51] | `freertos` | Espressif Systems (v4.4.7) | **ESP-IDF Programming Guide: FreeRTOS** | Concurrency primitives; shared SPI/serial resources still require correct application ownership. | [Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/system/freertos.html) |
| [52] | `platformio` | PlatformIO (n.d.) | **Unit Testing** | Supports the native NongMath test strategy; simulation does not validate power electronics or mechanical behavior. | [Link](https://docs.platformio.org/en/latest/advanced/unit-testing/index.html) |
| [53] | `clock` | Python Software Foundation (n.d.) | **time — Time access and conversions** | Elapsed-time measurement; record timer, timeout policy and whether failed requests are excluded. | [Link](https://docs.python.org/3/library/time.html) |
| [54] | `three` | Three.js contributors (n.d.) | **Three.js documentation** | Scene-graph transform and camera APIs; cite the vendored release separately from current documentation. | [Link](https://threejs.org/docs/) |
| [55] | `yaml` | YAML Language Development Team (2021) | **YAML Ain’t Markup Language (YAML) Version 1.2, Revision 1.2.2** | Sequence/config syntax; the firmware parser may support only a subset of the full language. | [Link](https://yaml.org/spec/1.2.2/) |
| [56] | `sd` | SD Association (n.d.) | **Simplified Specifications** | SD/SPI storage background. Select the exact card/interface edition for hardware claims. | [Link](https://www.sdcard.org/downloads/pls/) |
| [57] | `hri` | M. A. Goodrich and A. C. Schultz (2007) | **Human–Robot Interaction: A Survey** | Human-robot interaction background for operator controls, feedback and evaluation. | [10.1561/1100000005](https://doi.org/10.1561/1100000005) |
| [58] | `iso9283` | ISO (1998) | **ISO 9283:1998 — Manipulating industrial robots — Performance criteria and related test methods** | Accuracy/repeatability terminology for an adapted experiment. Mice is not certified as an ISO 9283 test system. | [Link](https://www.iso.org/standard/22244.html) |
| [59] | `iso12100` | ISO (2010) | **ISO 12100:2010 — Safety of machinery — General principles for design — Risk assessment and risk reduction** | Framework for assessing motion, pinch, power and unexpected-start hazards; no compliance claim. | [Link](https://www.iso.org/standard/51528.html) |
| [60] | `iso13850` | ISO (2015) | **ISO 13850:2015 — Safety of machinery — Emergency stop function — Principles for design** | Related safety reference. An ordinary browser STOP command is not evidence of a compliant emergency stop. | [Link](https://www.iso.org/standard/59970.html) |
| [61] | `iso9241` | ISO (2019) | **ISO 9241-210:2019 — Ergonomics of human-system interaction — Part 210: Human-centred design for interactive systems** | Operator-oriented design and usability-study planning; not proof of usability from screenshots alone. | [Link](https://www.iso.org/standard/77520.html) |
| [62] | `gum` | JCGM (2008) | **Evaluation of measurement data — Guide to the expression of uncertainty in measurement** | Type A/B uncertainty, sensitivity coefficients and combined/expanded uncertainty. | [Link](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf) |
| [63] | `mean-ci` | NIST/SEMATECH (n.d.) | **e-Handbook of Statistical Methods: Confidence Limits for the Mean** | Student-t interval for the mean with assumptions; not an interval containing 95% of individual latency observations. | [Link](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |
| [64] | `binomial` | NIST/SEMATECH (n.d.) | **e-Handbook of Statistical Methods: Confidence Intervals for a Binomial Proportion** | Uncertainty in packet success or recognition success rates; trials must support the independence model. | [Link](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm) |
| [65] | `statistics` | Python Software Foundation (n.d.) | **statistics — Mathematical statistics functions** | Document descriptive statistics and percentile convention; project percentile() must be cited as its own implementation. | [Link](https://docs.python.org/3/library/statistics.html) |
| [66] | `hrtime` | W3C (n.d.) | **High Resolution Time** | Browser elapsed-time measurement; timestamps from different PCs need synchronization before subtraction. | [Link](https://www.w3.org/TR/hr-time-3/) |
| [67] | `webaudio` | W3C (n.d.) | **Web Audio API 1.1** | Related real-time audio design; do not claim the current MediaRecorder path uses an AudioWorklet. | [Link](https://www.w3.org/TR/webaudio/) |
| [68] | `craig` | John J. Craig (2017) | **Introduction to Robotics: Mechanics and Control** | Forward/inverse kinematics, Jacobians, and dynamics. | [Link](https://www.pearson.com/en-us/subject-catalog/p/introduction-to-robotics-mechanics-and-control/P200000003304/9780133489798) |
| [69] | `spong` | Mark W. Spong, Seth Hutchinson, and M. Vidyasagar (2020) | **Robot Modeling and Control** | Kinematics, dynamics, and independent joint control. | [Link](https://www.wiley.com/en-us/Robot+Modeling+and+Control%2C+2nd+Edition-p-9781119523994) |
| [70] | `corke` | P. Corke, W. Jachimczyk and R. Pillat (2023) | **Robotics, Vision and Control: Fundamental Algorithms in MATLAB** | Fundamentals of robotics and vision. Trajectory generation and robot arms. | [10.1007/978-3-031-07262-8](https://link.springer.com/book/10.1007/978-3-031-07262-8) |
| [71] | `siciliano` | Bruno Siciliano, Lorenzo Sciavicco, Luigi Villani, and Giuseppe Oriolo (2009) | **Robotics: Modelling, Planning and Control** | Kinematic redundancy, singularity robustness, and trajectory planning. | [10.1007/978-1-84628-642-1](https://link.springer.com/book/10.1007/978-1-84628-642-1) |
| [72] | `biagiotti` | Luigi Biagiotti and Claudio Melchiorri (2009) | **Trajectory Planning for Automatic Machines and Robots** | Detailed time-scaling profiles including trigonometric and polynomial laws. | [10.1007/978-3-540-85629-0](https://link.springer.com/book/10.1007/978-3-540-85629-0) |
| [73] | `flash` | Tamar Flash and Neville Hogan (1985) | **The coordination of arm movements: An experimentally confirmed mathematical model** | Minimum-jerk trajectories and bell-shaped velocity profiles in human arm movements. | [10.1523/JNEUROSCI.05-07-01688.1985](https://www.jneurosci.org/content/5/7/1688) |
| [74] | `maciejewski` | A. A. Maciejewski and C. A. Klein (1988) | **Numerical filtering for the operation of robotic manipulators through kinematically singular configurations** | Original methodology for using Damped Least Squares to handle singularities. | [10.1002/rob.4620050603](https://onlinelibrary.wiley.com/doi/abs/10.1002/rob.4620050603) |
| [75] | `nakamura` | Y. Nakamura and H. Hanafusa (1986) | **Inverse Kinematic Solutions With Singularity Robustness for Robot Manipulator Control** | Singularity robust inverse kinematics formulation. | [10.1115/1.3143764](https://asmedigitalcollection.asme.org/dynamicsystems/article-abstract/108/3/163/409605/) |
| [76] | `chiaverini` | Stefano Chiaverini (1997) | **Singularity-robust task-priority redundancy resolution for real-time kinematic control of robot manipulators** | Redundancy resolution and DLS task-priority IK. | [10.1109/70.585902](https://ieeexplore.ieee.org/document/585902) |
| [77] | `hibbeler` | R. C. Hibbeler (2015) | **Engineering Mechanics: Dynamics** | Fundamental Newton-Euler equations of motion (F=ma). | [Link](https://www.pearson.com/en-us/subject-catalog/p/Hibbeler-Mastering-Engineering-without-Pearson-e-Text-Instant-Access-for-Engineering-Mechanics-Dynamics-14th-Edition/P200000007372) |
| [78] | `franklin` | Gene F. Franklin, J. David Powell, and Abbas Emami-Naeini (2018) | **Feedback Control of Dynamic Systems** | PID design, tuning, and feedback loops. | [Link](https://www.pearson.com/en-us/subject-catalog/p/feedback-control-of-dynamic-systems/P200000003343/9780137516834) |
| [80] | `modbus` | Modbus Organization (2006) | **Modbus over Serial Line Specification and Implementation Guide V1.02** | Common industrial RS-485 framing protocol (for comparison with custom protocol). | [Link](https://modbus.org/docs/Modbus_over_serial_line_V1_02.pdf) |
| [81] | `incropera` | T. L. Bergman, A. S. Lavine, F. P. Incropera and D. P. DeWitt (2017) | **Fundamentals of Heat and Mass Transfer** | Lumped thermal-model background. No fitted thermal constants or measured servo temperature limit is supplied by this reference. | [Link](https://bcs.wiley.com/he-bcs/Books?action=index&bcsId=10769&itemId=1119320429) |
| [82] | `meriam` | J. L. Meriam and L. G. Kraige (2012) | **Engineering Mechanics: Statics** | Equilibrium equations ΣF = 0, ΣM = 0; center of mass calculations for arm segment holding torque. | [Link](https://bcs.wiley.com/he-bcs/Books?action=index&bcsId=6549&itemId=0470614730) |
| [83] | `hughes` | Austin Hughes and Bill Drury (2013) | **Electric Motors and Drives: Fundamentals, Types and Applications** | DC servo motor torque generation τ = K_t * I, back-EMF V = Ke * ω, and thermal limits. | [10.1016/C2011-0-07555-5](https://www.sciencedirect.com/book/9780080983325/electric-motors-and-drives) |
| [84] | `krishnan` | R. Krishnan (2001) | **Electric Motor Drives: Modeling, Analysis, and Control** | Electromechanical differential equations V = IR + L(dI/dt) + Ke*ω and armature inductance effects. | [Link](https://in.pearson.com/content/dam/region-growth/india/pearson-india/Support/pdf/ECE_2017.pdf) |
| [85] | `faux` | D. A. Faux and J. Godolphin (2019) | **Manual timing in physics experiments: Error and uncertainty** | Anticipated visual-event timing: the reported experiment has single-event mean 0.11 s and standard deviation 0.07 s; start–stop standard deviation about 0.10 s under its assumptions. These are not universal Mice uncertainties. | [10.1119/1.5085437](https://doi.org/10.1119/1.5085437) |
| [86] | `gear-efficiency` | Q. Du, G. Yang, W. Wang, C.-Y. Chen and Z. Fang (2025) | **Modeling and Analysis of Transmission Efficiency for 3K Planetary Gearbox with Flexure-Based Carrier for Backdrivable Robot Joints** | Specific preloaded 3K planetary prototypes; efficiency depends on preload and load. Does not establish 80% efficiency for the Mice hobby servos. | [10.3390/act14040173](https://www.mdpi.com/2076-0825/14/4/173) |
| [88] | `tmech21` | S. Crispel, P. Lopez Garcia, E. Saerens, A. Varadharajan, T. Verstraten, B. Vanderborght and D. Lefeber (2021) | **A Novel Wolfrom-Based Gearbox for Robotic Actuators** | Related Wolfrom gearbox design; not a measurement of Mice servo efficiency. | [10.1109/TMECH.2021.3079471](https://doi.org/10.1109/TMECH.2021.3079471) |
| [90] | `tec15` | O. Wallscheid and J. Böcker (2016) | **Global Identification of a Low-Order Lumped-Parameter Thermal Network for Permanent Magnet Synchronous Motors** | Identified lumped thermal network for PMSMs; related method only, not a validated thermal model of a hobby servo. | [10.1109/TEC.2015.2473673](https://doi.org/10.1109/TEC.2015.2473673) |
| [91] | `tro06` | K. Kozak, Q. Zhou and J. Wang (2006) | **Static analysis of cable-driven manipulators with non-negligible cable mass** | Related cable-driven robot statics with cable sag. Mice has not been established as this type of cable-driven mechanism; not used as evidence for its arm torque. | [10.1109/TRO.2006.870659](https://doi.org/10.1109/TRO.2006.870659) |
| [92] | `stribeck` | B. Armstrong-Hélouvry, P. Dupont, and C. Canudas de Wit (1994) | **A survey of models, analysis tools and compensation methods for the control of machines with friction** | Static friction, Coulomb friction, and viscous damping in geared servo mechanisms. | [10.1016/0005-1098(94)90209-7](https://doi.org/10.1016/0005-1098(94)90209-7) |
| [94] | `pololu-servo` | Pololu Corporation (n.d.) | **Pololu Maestro USB Servo Controller User's Guide** | Documents the Maestro controller, not the internal deadband of every hobby servo or the ESP32Servo backend. | [Link](https://www.pololu.com/docs/0J40) |
| [95] | `udp` | L. Eggert, G. Fairhurst and G. Shepherd (2017) | **UDP Usage Guidelines** | Datagram sizing, unreliable delivery and controlled networks. UDP itself does not guarantee ordering, bounded delay or congestion control. | [10.17487/RFC8085](https://www.rfc-editor.org/rfc/rfc8085.html) |
| [96] | `sampling` | S. W. Smith (n.d.) | **The Scientist and Engineer’s Guide to Digital Signal Processing: The Sampling Theorem** | Band-limited sampling and aliasing. The theoretical Nyquist boundary is not a practical anti-alias filter specification. | [Link](https://www.dspguide.com/ch3/2.htm) |
| [97] | `winrt-tts` | Microsoft (n.d.) | **SpeechSynthesizer Class (Windows.Media.SpeechSynthesis)** | Actual WinRT speech interface called by tts.ps1; uses installed voices. This is not the browser Web Speech API. | [Link](https://learn.microsoft.com/en-ca/uwp/api/windows.media.speechsynthesis.speechsynthesizer?view=winrt-28000) |
| [98] | `whisper-streaming` | D. Macháček, R. Dabre and O. Bojar (2023) | **Turning Whisper into Real-Time Transcription System** | Streaming transcription strategy for a model designed for complete audio segments; related future work, not verified as installed in Mice. | [10.18653/v1/2023.ijcnlp-demo.3](https://aclanthology.org/2023.ijcnlp-demo.3/) |
| [99] | `nist-face` | P. Grother, M. Ngan and K. Hanaoka (2019) | **Face Recognition Vendor Test Part 3: Demographic Effects** | Supports evaluating false matches and false non-matches across declared test groups; published results do not transfer directly to the Mice backend. | [10.6028/NIST.IR.8280](https://www.nist.gov/publications/face-recognition-vendor-test-part-3-demographic-effects) |
| [100] | `iso19795` | ISO/IEC (2021) | **ISO/IEC 19795-1:2021 — Information technology — Biometric performance testing and reporting — Part 1: Principles and framework** | Biometric testing/reporting framework. Full clauses must be consulted before claiming conformance. | [Link](https://www.iso.org/standard/73515.html) |
| [101] | `cpp-integral` | ISO/IEC JTC1/SC22/WG21 (n.d.) | **C++ working draft: Integral conversions** | Explains negative integer conversion to an unsigned type; use with the actual Arduino byte typedef. This is a public draft mirror, not a purchased ISO edition. | [Link](https://eel.is/c++draft/conv.integral) |
| [102] | `pololu-electrical` | J. Malášek (Pololu) (2011) | **Electrical characteristics of servos and introduction to the servo control interface** | Servo power/current and pulse-interface background; pulse-position mapping and limits depend on the servo. | [Link](https://www.pololu.com/blog/16/electrical-characteristics-of-servos-and-introduction-to-the-servo-control-interface) |
| [103] | `nist-units` | NIST (n.d.) | **Guide to the SI, Appendix B.9: Factors for units listed by kind of quantity or field of science** | Distinguish mass kg from force kgf. 1 kgf·cm = 0.0980665 N·m, derived from the listed kgf and length conversions. | [Link](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9) |
| [104] | `least-squares` | NIST/SEMATECH (n.d.) | **e-Handbook of Statistical Methods: Linear Least Squares Regression** | Least-squares model fitting for a proposed calibration experiment; inspect residuals and assumptions, not just the fitted slope. | [Link](https://www.itl.nist.gov/div898/handbook/pmd/section1/pmd141.htm) |
| [137] | `whitney-resolved-rate` | D. E. Whitney (1969) | **Resolved Motion Rate Control of Manipulators and Human Prostheses** | Foundational formulation of resolved motion rate control; uses the manipulator Jacobian matrix J(q) to map desired end-effector Cartesian velocities to commanded joint rates via q_dot = J^(-1) v. Establishes the mathematical basis for differential kinematics and inverse Jacobian solvers. | [10.1109/tmms.1969.299896](https://doi.org/10.1109/tmms.1969.299896) |
| [138] | `krause-motor-dynamics` | P. C. Krause, O. Wasynczuk, and S. D. Sudhoff (2002) | **Analysis of Electric Machinery and Drive Systems** | Comprehensive electromechanical differential equations for DC motors: V = R I + L dI/dt + K_e omega, electromagnetic torque tau_e = K_t I, and rotor dynamic balance tau_e - tau_load = J domega/dt + B omega. | [Link](https://www.wiley.com/en-us/Analysis+of+Electric+Machinery+and+Drive+Systems%2C+3rd+Edition-p-9781118024294) |
| [139] | `rabiner-speech-dsp` | L. R. Rabiner and R. W. Schafer (2010) | **Theory and Applications of Digital Speech Processing** | Standard theory for digital speech analysis: framing, Hamming/Hann windowing, short-time Fourier transform (STFT), Mel-frequency filterbank energies, and cepstral feature representation. Groundwork for acoustic pre-processing in modern ASR. | [Link](https://www.pearson.com/en-us/subject-catalog/p/theory-and-applications-of-digital-speech-processing/P200000003507) |
| [140] | `tsai-camera-calib` | R. Y. Tsai (1987) | **A versatile camera calibration technique for high-accuracy 3D machine vision metrology using off-the-shelf TV cameras and lenses** | Landmark two-stage camera calibration technique utilizing the radial alignment constraint (RAC) to solve for 3D extrinsic orientation/position and intrinsic parameters (focal length, radial distortion coefficient kappa, optical center). | [10.1109/jra.1987.1087109](https://doi.org/10.1109/jra.1987.1087109) |
| [141] | `fong-service-hri` | T. Fong, I. Nourbakhsh, and K. Dautenhahn (2003) | **A survey of socially interactive robots** | Authoritative review of socially interactive and service robots: examines speech dialogue interfaces, gesture expression, user proxemics, and safe interaction modalities in human environments. | [10.1016/s0921-8890(02)00372-x](https://doi.org/10.1016/s0921-8890(02)00372-x) |
| [142] | `lowe-sift-vision` | D. G. Lowe (2004) | **Distinctive Image Features from Scale-Invariant Keypoints** | Classical scale-invariant feature transform (SIFT): identifies scale-space extrema in difference-of-Gaussian pyramids, assigns consistent orientation, and generates local 128-dimensional invariant feature vectors for object/face localization. | [10.1023/b:visi.0000029664.99615.94](https://doi.org/10.1023/b:visi.0000029664.99615.94) |

---
## 4. Master Equation Catalog

### Card: Servo Gearbox Efficiency (ประสิทธิภาพชุดเกียร์เซอร์โว)
- **ID**: `servo-efficiency` | **Group**: *Embedded hardware* | **Status**: `BACKGROUND`

```text
η = P_out/P_in = τ_out ω_out/(τ_in ω_in)
N = ω_in/ω_out; τ_out = η N τ_in (steady motoring, nonzero speed)
```

- **English Description**: Use efficiency to relate shaft powers for a defined gearbox and operating point. Efficiency varies with load, speed, lubrication and direction. A manufacturer servo output-shaft torque already includes its internal gearbox; do not multiply it by that internal reduction again.
- **คำอธิบายภาษาไทย**: ประสิทธิภาพขึ้นกับโหลด ความเร็ว และสภาพชุดเกียร์ ต้องวัดหรือใช้ข้อมูลของรุ่นจริง ค่าแรงบิดที่เพลาออกของเซอร์โวรวมผลของเกียร์ภายในแล้ว จึงไม่คูณอัตราทดภายในซ้ำ
- **Units & Variables**: η: dimensionless; N: reduction ratio; τ: N·m; ω: rad/s; P: W
- **Engineering Caveat / ข้อควรระวัง**: Removed universal η = 0.8 and 20–30% continuous/stall-torque rules. At stall, shaft-power efficiency is not a torque-rating conversion. Determine continuous limits by manufacturer data and a thermal/load experiment.
- **Implementation Code Location**:
  * `firmware/config/servos.json` (Line 1): *Servo registry: sizing context, not an efficiency model*
- **Supporting References**:
  * `[86]` Q. Du, G. Yang, W. Wang, C.-Y. Chen and Z. Fang (2025) — *Modeling and Analysis of Transmission Efficiency for 3K Planetary Gearbox with Flexure-Based Carrier for Backdrivable Robot Joints* ([Link](https://www.mdpi.com/2076-0825/14/4/173))
  * `[88]` S. Crispel, P. Lopez Garcia, E. Saerens, A. Varadharajan, T. Verstraten, B. Vanderborght and D. Lefeber (2021) — *A Novel Wolfrom-Based Gearbox for Robotic Actuators* ([Link](https://doi.org/10.1109/TMECH.2021.3079471))
  * `[83]` Austin Hughes and Bill Drury (2013) — *Electric Motors and Drives: Fundamentals, Types and Applications* ([Link](https://www.sciencedirect.com/book/9780080983325/electric-motors-and-drives))
  * `[102]` J. Malášek (Pololu) (2011) — *Electrical characteristics of servos and introduction to the servo control interface* ([Link](https://www.pololu.com/blog/16/electrical-characteristics-of-servos-and-introduction-to-the-servo-control-interface))

---

### Card: Static Torque with Distributed Mass (แรงบิดสถิตจากการกระจายมวล)
- **ID**: `static-torque-arm` | **Group**: *Nong — the humanoid* | **Status**: `BACKGROUND`

```text
τ_axis = axis_unit · Σ_i (r_i × m_i g_vector)
For coplanar loads: |τ| = Σ_i m_i g d_perp_i
Uniform horizontal arm alone: |τ_arm| = m_arm g L/2
1 kgf·cm = 0.0980665 N·m
```

- **English Description**: Calculate every component moment about the selected joint axis. Use each component centre of mass and include payload and downstream servos. L/2 applies only to a uniform straight link; take signed moments when contributions oppose.
- **คำอธิบายภาษาไทย**: คำนวณโมเมนต์ของแต่ละชิ้นรอบแกนข้อต่อ โดยใช้มวลคูณความเร่งโน้มถ่วงและระยะแขนตั้งฉาก รวมโหลดและเซอร์โวปลายแขน ค่า L/2 ใช้ได้กับแท่งสม่ำเสมอเท่านั้น
- **Units & Variables**: m: kg; r,d,L: m; g: m/s²; τ: N·m
- **Engineering Caveat / ข้อควรระวัง**: The previous mass × distance formula omitted g when claiming N·m. kg·cm is not a force-moment unit; write kgf·cm if using gravitational units. No measured 3.3 kgf·cm result is asserted.
- **Implementation Code Location**:
  * `scient_test/tests/T1_nong_module.md` (Line 9): *Physical sizing context; proposed calculation, not a firmware torque solver*
- **Supporting References**:
  * `[82]` J. L. Meriam and L. G. Kraige (2012) — *Engineering Mechanics: Statics* ([Link](https://bcs.wiley.com/he-bcs/Books?action=index&bcsId=6549&itemId=0470614730))
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))
  * `[103]` NIST (n.d.) — *Guide to the SI, Appendix B.9: Factors for units listed by kind of quantity or field of science* ([Link](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9))
  * `[108]` H. Wongsuwarn and D. Laowattana (2006) — *Experimental Study for a FIBO Humanoid Robot* ([Link](https://doi.org/10.1109/ramech.2006.252690))

---

### Card: Manual Stopwatch Measurement Error (ความคลาดเคลื่อนจากการจับเวลาด้วยมือ)
- **ID**: `human-reaction-time` | **Group**: *Software tests and validation* | **Status**: `BACKGROUND`

```text
t_measured = t_true + e_stop - e_start
u²(t_measured) = u²(e_stop)+u²(e_start)-2 cov(e_stop,e_start)
Independent equal-variance events: u_interval = √2 u_event
```

- **English Description**: Start and stop reactions can share a bias that cancels, while random variation remains. Faux and Godolphin report about 0.07 s single-event SD and 0.10 s interval SD for their anticipated visual events; estimate uncertainty for your own measurement protocol.
- **คำอธิบายภาษาไทย**: ความคลาดเคลื่อนตอนเริ่มและหยุดอาจหักล้างกันบางส่วน แต่ความแปรปรวนยังอยู่ งานอ้างอิงพบส่วนเบี่ยงเบนมาตรฐานประมาณ 0.07 วินาทีต่อเหตุการณ์ และ 0.10 วินาทีต่อช่วงเวลาภายใต้เงื่อนไขของงานนั้น ต้องประเมินใหม่สำหรับวิธีทดลองของโครงการ
- **Units & Variables**: t,e,u: s; covariance: s²
- **Engineering Caveat / ข้อควรระวัง**: Do not call ±0.2 s a universal standard deviation, confidence interval or guaranteed bound. A software timestamp also needs a defined physical event and clock resolution.
- **Implementation Code Location**:
  * `scient_test/tests/T1_nong_module.md` (Line 18): *Protocol distinguishes app timing from observations by eye*
- **Supporting References**:
  * `[85]` D. A. Faux and J. Godolphin (2019) — *Manual timing in physics experiments: Error and uncertainty* ([Link](https://doi.org/10.1119/1.5085437))
  * `[62]` JCGM (2008) — *Evaluation of measurement data — Guide to the expression of uncertainty in measurement* ([Link](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf))
  * `[53]` Python Software Foundation (n.d.) — *time — Time access and conversions* ([Link](https://docs.python.org/3/library/time.html))

---

### Card: DC Servo Motor Electromechanics (กลศาสตร์ไฟฟ้าของเซอร์โวมอเตอร์กระแสตรง)
- **ID**: `servo-motor-model` | **Group**: *Embedded hardware* | **Status**: `BACKGROUND`

```text
V = RI + L dI/dt + K_e ω
τ_e = K_t I
J dω/dt = τ_e - τ_load - τ_friction
```

- **English Description**: A simplified constant-flux DC motor model relates winding voltage and current to electromagnetic torque. K_t is treated as constant only within the model assumptions. Gearbox output torque and continuous thermal limits require further modelling or measurements.
- **คำอธิบายภาษาไทย**: แบบจำลองมอเตอร์กระแสตรงภายใต้สมมติฐานฟลักซ์คงที่ เชื่อมแรงดันและกระแสกับแรงบิดแม่เหล็กไฟฟ้า ต้องแยกแรงบิดเพลามอเตอร์ออกจากแรงบิดหลังเกียร์ และวัดขีดจำกัดทางความร้อนของรุ่นจริง
- **Units & Variables**: V: V; I: A; R: Ω; L: H; K_e: V·s/rad; K_t: N·m/A; J: kg·m²; ω: rad/s
- **Engineering Caveat / ข้อควรระวัง**: This model is background, not a current/torque observer implemented in Mice. Identify R, L, K_e, K_t and inertia before numerical predictions.
- **Implementation Code Location**:
  * `firmware/config/servos.json` (Line 1): *Motor-sizing context; electrical state equations are not implemented here*
- **Supporting References**:
  * `[83]` Austin Hughes and Bill Drury (2013) — *Electric Motors and Drives: Fundamentals, Types and Applications* ([Link](https://www.sciencedirect.com/book/9780080983325/electric-motors-and-drives))
  * `[84]` R. Krishnan (2001) — *Electric Motor Drives: Modeling, Analysis, and Control* ([Link](https://in.pearson.com/content/dam/region-growth/india/pearson-india/Support/pdf/ECE_2017.pdf))
  * `[5]` K. J. Åström and R. M. Murray (2008) — *Feedback Systems: An Introduction for Scientists and Engineers* ([Link](https://authors.library.caltech.edu/records/yzs24-xsx88))
  * `[102]` J. Malášek (Pololu) (2011) — *Electrical characteristics of servos and introduction to the servo control interface* ([Link](https://www.pololu.com/blog/16/electrical-characteristics-of-servos-and-introduction-to-the-servo-control-interface))
  * `[117]` M. Hayashi, Y. Koide, K. Matsuhara, S. Ushida, H. Oku, and W. Kongprawechnon (2017) — *Adaptive modeling and compliance control for RC servo motor* ([Link](https://doi.org/10.23919/sice.2017.8105557))
  * `[122]` J. Srisertpol and C. Khajorntraidet (2009) — *Estimation of DC motor variable torque using adaptive compensation* ([Link](https://doi.org/10.1109/ccdc.2009.5191882))
  * `[126]` N. Kongchoo, P. Santiprapan, and N. Jindapetch (2022) — *Mathematical Model and PI Controller Design Based on Indirect Vector Control for Permanent Magnet Synchronous Motor* ([Link](https://doi.org/10.37936/ecti-cit.2022163.245351))
  * `[138]` P. C. Krause, O. Wasynczuk, and S. D. Sudhoff (2002) — *Analysis of Electric Machinery and Drive Systems* ([Link](https://www.wiley.com/en-us/Analysis+of+Electric+Machinery+and+Drive+Systems%2C+3rd+Edition-p-9781118024294))

---

### Card: Static Mechanics (Holding Torque) (กลศาสตร์สถิต (แรงบิดต้านทานเพื่อรักษาสมดุล))
- **ID**: `statics-joints` | **Group**: *Nong — the humanoid* | **Status**: `BACKGROUND`

```text
ΣF = 0; ΣM = 0
τ_hold = g(q) - J(q)ᵀ F_external
Equivalently τ_hold = g(q) + J(q)ᵀ F_resist, with F_resist = -F_external
```

- **English Description**: The sign depends on whether the wrench means the environment acting on the robot or the robot resisting it. Express wrench and Jacobian in matching frames and at matching reference points; g(q) denotes gravity-compensation torque.
- **คำอธิบายภาษาไทย**: เครื่องหมายขึ้นกับนิยามแรงจากสิ่งแวดล้อมหรือแรงต้านของหุ่นยนต์ ต้องใช้กรอบพิกัดและจุดอ้างอิงเดียวกันสำหรับแรงและจาโคเบียน โดย g(q) คือแรงบิดชดเชยแรงโน้มถ่วง
- **Units & Variables**: J: task velocity per joint rate; F: wrench (N, N·m); τ,g(q): N·m
- **Engineering Caveat / ข้อควรระวัง**: No gravity-compensation torque controller is established by the current position-command code.
- **Implementation Code Location**:
  * `nong/main_python_set_nong/web/app.js` (Line 1262): *Geometry context for proposed load model*
- **Supporting References**:
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))
  * `[82]` J. L. Meriam and L. G. Kraige (2012) — *Engineering Mechanics: Statics* ([Link](https://bcs.wiley.com/he-bcs/Books?action=index&bcsId=6549&itemId=0470614730))
  * `[69]` Mark W. Spong, Seth Hutchinson, and M. Vidyasagar (2020) — *Robot Modeling and Control* ([Link](https://www.wiley.com/en-us/Robot+Modeling+and+Control%2C+2nd+Edition-p-9781119523994))
  * `[108]` H. Wongsuwarn and D. Laowattana (2006) — *Experimental Study for a FIBO Humanoid Robot* ([Link](https://doi.org/10.1109/ramech.2006.252690))
  * `[116]` A. Suebsomran, N. Manoch, and P. Kwanthong (2022) — *Development and Control of a Lower Limb Exoskeleton Robot* ([Link](https://doi.org/10.1109/iceccme55909.2022.9988414))
  * `[122]` J. Srisertpol and C. Khajorntraidet (2009) — *Estimation of DC motor variable torque using adaptive compensation* ([Link](https://doi.org/10.1109/ccdc.2009.5191882))
  * `[133]` P. Sutyasadi, M. Wicaksono, and D. Maneetham (2023) — *Improvement Control of a Three Axis Articulated Robotic Arm Using PID Cascade Control* ([Link](https://doi.org/10.1109/citsm60085.2023.10455548))

---

### Card: Heat Transfer (Motor Thermal Model) (การถ่ายเทความร้อน (แบบจำลองทางความร้อนของมอเตอร์))
- **ID**: `thermodynamics-motor` | **Group**: *Embedded hardware* | **Status**: `BACKGROUND`

```text
P_conv = h A (T_s - T_ambient)
C_th d(ΔT)/dt = P_loss - ΔT/R_th
Constant loss, ΔT(0)=0: ΔT(t)=P_loss R_th [1-exp(-t/(R_th C_th))]
Steady state: ΔT = P_loss R_th
```

- **English Description**: A single thermal resistance/capacitance is a reduced model for transient heating. Winding I²R is one loss term; friction, electronics and conduction paths can matter. Fit and validate thermal parameters over the intended loads.
- **คำอธิบายภาษาไทย**: แบบจำลองความต้านทานและความจุความร้อนใช้ประมาณอุณหภูมิที่เปลี่ยนตามเวลา ต้องรวมแหล่งความสูญเสียที่เกี่ยวข้องและวัดค่าพารามิเตอร์ ขีดจำกัดไฟตกของบอร์ดไม่ใช่ขีดจำกัดอุณหภูมิมอเตอร์
- **Units & Variables**: P: W; h: W/(m²·K); A: m²; R_th: K/W; C_th: J/K; ΔT: K
- **Engineering Caveat / ข้อควรระวัง**: Lumped temperature assumes small internal gradients or an empirically validated equivalent model. No servo temperature data or safe continuous load is supplied by this page.
- **Implementation Code Location**:
  * `firmware/src/core/BrownoutGuard.cpp` (Line 1): *Electrical brownout context; not a temperature sensor or thermal controller*
- **Supporting References**:
  * `[81]` T. L. Bergman, A. S. Lavine, F. P. Incropera and D. P. DeWitt (2017) — *Fundamentals of Heat and Mass Transfer* ([Link](https://bcs.wiley.com/he-bcs/Books?action=index&bcsId=10769&itemId=1119320429))
  * `[90]` O. Wallscheid and J. Böcker (2016) — *Global Identification of a Low-Order Lumped-Parameter Thermal Network for Permanent Magnet Synchronous Motors* ([Link](https://doi.org/10.1109/TEC.2015.2473673))
  * `[83]` Austin Hughes and Bill Drury (2013) — *Electric Motors and Drives: Fundamentals, Types and Applications* ([Link](https://www.sciencedirect.com/book/9780080983325/electric-motors-and-drives))

---

### Card: Newton-Euler Dynamics (Sigma F = ma) (พลศาสตร์นิวตัน-ออยเลอร์ (ΣF = ma))
- **ID**: `dynamics-f-ma` | **Group**: *Nong — the humanoid* | **Status**: `BACKGROUND`

```text
ΣF = m a_COM
ΣM_COM = I_COM α + ω × (I_COM ω)
τ = M(q)q̈ + C(q,q̇)q̇ + g(q) + τ_friction - J(q)ᵀ F_external
```

- **English Description**: The vector Newton–Euler equation includes the gyroscopic term; Στ = Iα alone applies to restricted cases such as planar fixed-axis rotation. A manipulator dynamics model needs measured masses, centres of mass, inertias and clear force signs.
- **คำอธิบายภาษาไทย**: สมการนิวตัน–ออยเลอร์แบบสามมิติต้องรวมพจน์ไจโรสโคปิก รูป Στ = Iα ใช้กับกรณีจำกัด เช่น การหมุนรอบแกนคงที่ ต้องระบุมวล จุดศูนย์กลางมวล และโมเมนต์ความเฉื่อยของแต่ละชิ้น
- **Units & Variables**: q: rad; q̇: rad/s; q̈: rad/s²; τ: N·m; M: joint-space inertia; I_COM: kg·m²
- **Engineering Caveat / ข้อควรระวัง**: Current motion code generates kinematic position commands; it does not establish this complete inverse-dynamics controller.
- **Implementation Code Location**:
  * `firmware/src/modules/nong/NongMath.h` (Line 98): *Position-trajectory context; full dynamics are related analysis*
- **Supporting References**:
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))
  * `[77]` R. C. Hibbeler (2015) — *Engineering Mechanics: Dynamics* ([Link](https://www.pearson.com/en-us/subject-catalog/p/Hibbeler-Mastering-Engineering-without-Pearson-e-Text-Instant-Access-for-Engineering-Mechanics-Dynamics-14th-Edition/P200000007372))
  * `[69]` Mark W. Spong, Seth Hutchinson, and M. Vidyasagar (2020) — *Robot Modeling and Control* ([Link](https://www.wiley.com/en-us/Robot+Modeling+and+Control%2C+2nd+Edition-p-9781119523994))
  * `[71]` Bruno Siciliano, Lorenzo Sciavicco, Luigi Villani, and Giuseppe Oriolo (2009) — *Robotics: Modelling, Planning and Control* ([Link](https://link.springer.com/book/10.1007/978-1-84628-642-1))
  * `[115]` V. Sangveraphunsiri and K. Chooprasird (2010) — *Dynamics and control of a 5-DOF manipulator based on an H-4 parallel mechanism* ([Link](https://doi.org/10.1007/s00170-010-2722-3))
  * `[116]` A. Suebsomran, N. Manoch, and P. Kwanthong (2022) — *Development and Control of a Lower Limb Exoskeleton Robot* ([Link](https://doi.org/10.1109/iceccme55909.2022.9988414))
  * `[123]` N. Ajjanaromvat and M. Parnichkun (2018) — *Trajectory tracking using online learning LQR with adaptive learning control of a leg-exoskeleton for disorder gait rehabilitation* ([Link](https://doi.org/10.1016/j.mechatronics.2018.03.003))
  * `[131]` P. Neranon and R. Bicker (2016) — *Force/position control of a robot manipulator for human-robot interaction* ([Link](https://doi.org/10.2298/tsci151005036n))
  * `[138]` P. C. Krause, O. Wasynczuk, and S. D. Sudhoff (2002) — *Analysis of Electric Machinery and Drive Systems* ([Link](https://www.wiley.com/en-us/Analysis+of+Electric+Machinery+and+Drive+Systems%2C+3rd+Edition-p-9781118024294))

---

### Card: Servo mounting offset (trim) (ค่าชดเชยการติดตั้งเซอร์โว)
- **ID**: `mounting-offset` | **Group**: *Nong — the humanoid* | **Status**: `IMPLEMENTED`

```text
trim<sub>servo</sub> = offset<sub>joint</sub> &times; gear/pinion
offset<sub>joint</sub> = trim<sub>servo</sub> &divide; gear/pinion
```

- **English Description**: The spline spacing depends on the fitted servo; no universal 14° increment is assumed. OFFSET is entered in joint degrees and converted to stored servo-degree trim using servoPerJoint(). Calibration belongs to the measured assembly, not a textbook constant.
- **คำอธิบายภาษาไทย**: แปลงค่าชดเชยจากองศาข้อต่อเป็นองศาเพลาเซอร์โวด้วยอัตราทด ค่าจริงต้องวัดจากหุ่นยนต์
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Engineering Caveat / ข้อควรระวัง**: trim is added BEFORE the invert (see the entry below), which is what makes an inverted joint need no special case: the correction travels through the mirror exactly as the joint term does, so +1&deg; of offset moves the arm the way +1&deg; of joint angle would. Moving trim after the invert would silently reverse every plus button on the page.
- **Implementation Code Location**:
  * `firmware/src/modules/nong/NongModule.h` (Line 230): *servoPerJoint() — the ratio both users share*
  * `firmware/src/modules/nong/NongModule.cpp` (Line 697): *the OFFSET command*
  * `firmware/src/modules/nong/NongModule.cpp` (Line 506): *SETZERO, the all-ten version*
- **Supporting References**:
  * `[6]` KHK Gears (n.d.) — *Calculation of Gear Dimensions* ([Link](https://khkgears.net/new/gear_knowledge/gear_technical_reference/calculation_gear_dimensions.html))
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))

---

### Card: Joint angle to servo pulse (แปลงมุมข้อต่อเป็นความกว้างพัลส์)
- **ID**: `joint-to-pulse` | **Group**: *Nong — the humanoid* | **Status**: `IMPLEMENTED`

```text
servo = range/2 + (joint - 90) &times; gear/pinion + trim
&micro;s    = pulse<sub>min</sub> + servo/range &times; (pulse<sub>max</sub> - pulse<sub>min</sub>)
```

- **English Description**: Two different spaces, both measured from their centre: joint degrees (what a pose is written in, neutral 90) and servo degrees (how far the shaft turns). The gear maps between them, so a 270&deg; servo behind a 15:18 reduction and a 180&deg; servo behind 12:13 are driven correctly side by side — and every saved pose keeps working when a servo is swapped.
- **คำอธิบายภาษาไทย**: เป็นการแปลงเชิงเส้นตามค่าตั้งของแต่ละเซอร์โว ไม่ใช่ช่วงพัลส์มาตรฐานเดียวสำหรับทุกยี่ห้อ
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Engineering Caveat / ข้อควรระวัง**: The code clamps shaft angle, applies inversion, then rounds pulse width. Configured endpoints are not a universal 500–2500 µs standard; calibrate the actual servo without exceeding its permitted travel.
- **Implementation Code Location**:
  * `firmware/src/modules/nong/NongMath.h` (Line 35): *jointToServoDeg() and servoDegToUs()*
- **Supporting References**:
  * `[6]` KHK Gears (n.d.) — *Calculation of Gear Dimensions* ([Link](https://khkgears.net/new/gear_knowledge/gear_technical_reference/calculation_gear_dimensions.html))
  * `[17]` ESP32Servo contributors (n.d.) — *ESP32Servo* ([Link](https://github.com/madhephaestus/ESP32Servo))
  * `[14]` Espressif Systems (v4.4.7) — *ESP-IDF Programming Guide: LED Control (LEDC)* ([Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/peripherals/ledc.html))

---

### Card: The shortest a move may take (ระยะเวลาขั้นต่ำของการเคลื่อนที่)
- **ID**: `move-floor` | **Group**: *Nong — the humanoid* | **Status**: `IMPLEMENTED`

```text
v_i = max(maxDps_i, 1 degree/s)
T_code_ms = max(minMoveMs, floor(1000 × max_i(|Δq_i|/v_i)))
```

- **English Description**: This is the duration rule implemented by minDuration(). It bounds an average-speed calculation, with a configurable floor. For cosine time scaling, peak speed is π|Δq|/(2T); therefore the code rule alone does not establish a strict peak-speed bound.
- **คำอธิบายภาษาไทย**: สูตรในโค้ดจำกัดความเร็วเฉลี่ย ค่า 80 ms เป็นค่าที่โครงการเลือก ไม่ใช่ข้อกำหนดจากมาตรฐาน และยังต้องพิจารณาความเร็วสูงสุดของเส้นโค้ง
- **Units & Variables**: Δq in degrees; maxDps in degrees/s; result in ms.
- **Engineering Caveat / ข้อควรระวัง**: Do not derive the 80 ms design choice from a presumed 20 ms servo cycle without a recorded design argument and test. Compare firmware and Studio settings.
- **Implementation Code Location**:
  * `firmware/src/modules/nong/NongMath.h` (Line 67): *minDuration()*
  * `nong/main_python_set_nong/web/app.js` (Line 1588): *minTime() — Nong Studio's copy, which must stay identical*
- **Supporting References**:
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))

---

### Card: How long a move takes at show speed (เวลาของท่าที่กำหนดด้วยความเร็ว)
- **ID**: `show-time` | **Group**: *Nong — the humanoid* | **Status**: `IMPLEMENTED`

```text
T_requested_ms = max(minMoveMs, floor(1000 max_i|Δq_i| / max(speedDps,1)))
```

- **English Description**: durationFor() computes the requested time from the largest angle change and requested speed, with a minimum time. Additional minDuration() handling occurs at callers. This is a project scheduling rule, not proof of achievable peak speed under load.
- **คำอธิบายภาษาไทย**: คำนวณจากข้อต่อที่เปลี่ยนมุมมากที่สุด แล้วใช้ข้อจำกัดเวลาที่จุดเรียกใช้งาน ความเร็วจริงต้องวัดภายใต้โหลด
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Implementation Code Location**:
  * `firmware/src/modules/nong/NongMath.h` (Line 90): *durationFor()*
- **Supporting References**:
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))

---

### Card: The shape of every move (เส้นโค้งโคไซน์สำหรับเปลี่ยนท่า)
- **ID**: `ease` | **Group**: *Nong — the humanoid* | **Status**: `IMPLEMENTED`

```text
f(t) = 0.5 - 0.5 &times; cos(&pi;t),   t in 0..1
```

- **English Description**: The normalized position follows a half-cosine time scaling. Differentiating this project equation gives zero endpoint velocity and a mid-move speed maximum. Robotics trajectory references explain time scaling; the exact cosine derivative below is an explicit mathematical derivation.
- **คำอธิบายภาษาไทย**: ความเร็วเป็นศูนย์ที่ต้นและปลาย แต่ความเร่งอาจกระโดดเมื่อเชื่อมกับช่วงหยุด จึงไม่ใช่การรับประกันว่า jerk เป็นศูนย์
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Engineering Caveat / ข้อควรระวัง**: At joins to a stationary hold, acceleration jumps unless additional smoothing is applied. Zero endpoint velocity does not imply bounded jerk.
- **Implementation Code Location**:
  * `firmware/src/modules/nong/NongMath.h` (Line 98): *ease()*
- **Supporting References**:
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))

---

### Card: The shrug is a 4-bar linkage, and it is MEASURED (การประมาณค่าความสูงไหล่จากการวัด)
- **ID**: `shrug-4bar` | **Group**: *Nong — the humanoid* | **Status**: `IMPLEMENTED`

```text
rise(j) = a.rise + (b.rise - a.rise) &times; (j - a.j)/(b.j - a.j)
for the two measured points a, b either side of j — per shoulder
```

- **English Description**: shrugRise() linearly interpolates the recorded calibration points for each shoulder. Mechanism kinematics provides background, but the current function is an empirical lookup/interpolation, not an analytical four-bar solution. Archive the measured points, geometry and uncertainty.
- **คำอธิบายภาษาไทย**: ใช้การประมาณเชิงเส้นระหว่างจุดที่วัด ไม่ได้แก้สมการกลไกสี่บาร์จากมิติ CAD ต้องแนบตารางสอบเทียบจริง
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Engineering Caveat / ข้อควรระวัง**: The fallback picture is a project approximation. Do not describe it as a validated physical linkage model.
- **Implementation Code Location**:
  * `nong/main_python_set_nong/web/app.js` (Line 846): *shrugRise() — linear interpolation over the measured points*
- **Supporting References**:
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))
  * `[62]` JCGM (2008) — *Evaluation of measurement data — Guide to the expression of uncertainty in measurement* ([Link](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf))

---

### Card: Running a show from the move you clicked (การเริ่มเล่นต่อจากช่วงกลาง)
- **ID**: `resume` | **Group**: *Nong — the humanoid* | **Status**: `IMPLEMENTED`

```text
clock = hold<sub>0</sub>;  for each move i:  clock += t<sub>i</sub>  (inside &rarr; resume there),  clock += hold<sub>i</sub>  (inside &rarr; the next one)
first move written:  T = max( its own time, minTime(where the robot is &rarr; where it goes) )
```

- **English Description**: Added 2026-08-28 after the user reported the arm sweeping back to the first pose before running: *my body of robot will broke it hit other thing*. A file that starts in the middle cannot know where the arm is standing, so the one move with an unknown start is never allowed to be quicker than the distance needs. Never faster, only slower.
- **คำอธิบายภาษาไทย**: เป็นตรรกะเวลาของโครงการ ต้องทดสอบช่วงค้างท่าและการเคลื่อนจากตำแหน่งปัจจุบัน ไม่ใช่สูตรมาตรฐานเฉพาะ
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Engineering Caveat / ข้อควรระวัง**: The keyframes before the resume point are still walked for `speed`, which is STATE — skip that and the rest of the show runs at the wrong speed.
- **Implementation Code Location**:
  * `nong/main_python_set_nong/web/app.js` (Line 1724): *keyIndexAtMs() — which keyframe the clock is standing on*
  * `main_python/main.py` (Line 1448): *NongShow._play_once() — the hub's walk, same arithmetic*
- **Supporting References**:
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))
  * `[53]` Python Software Foundation (n.d.) — *time — Time access and conversions* ([Link](https://docs.python.org/3/library/time.html))

---

### Card: How far the rack moves per turn (ระยะเลื่อนของเฟืองสะพานต่อหนึ่งรอบ)
- **ID**: `rack-pinion` | **Group**: *Lift — rack and pinion* | **Status**: `IMPLEMENTED`

```text
mm_per_rev = &pi; &times; module &times; teeth
```

- **English Description**: For a rack and pinion with module m and tooth count z, pitch diameter d = mz and ideal travel per pinion revolution is πd. With m = 2 mm and z = 25, the derived value is approximately 157.08 mm/rev; check those against the fitted hardware.
- **คำอธิบายภาษาไทย**: ใช้เส้นรอบวงวงกลมพิตช์ หน่วยโมดูลต้องตรงกับหน่วยระยะทาง ความคลอนและการลื่นต้องวัดเพิ่ม
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Implementation Code Location**:
  * `firmware/src/core/ConfigStore.cpp` (Line 20): *mm_per_rev, the stored value*
- **Supporting References**:
  * `[6]` KHK Gears (n.d.) — *Calculation of Gear Dimensions* ([Link](https://khkgears.net/new/gear_knowledge/gear_technical_reference/calculation_gear_dimensions.html))
  * `[7]` ISO (1998) — *ISO 53:1998 — Cylindrical gears for general and heavy engineering — Standard basic rack tooth profile* ([Link](https://www.iso.org/standard/22643.html))

---

### Card: Speed in real units (ประมาณความเร็วลิฟต์จาก PWM)
- **ID**: `lift-speed` | **Group**: *Lift — rack and pinion* | **Status**: `IMPLEMENTED`

```text
v<sub>max</sub> = max_rpm / 60 &times; mm_per_rev
v       = v<sub>max</sub> &times; pwm / PWM<sub>max</sub>
```

- **English Description**: Open loop: the PWM duty is assumed proportional to speed. Good enough to ask for 200 mm/s and get roughly that, and it needs no encoder in the loop. Calibrate max_rpm by comparing the measured m/s shown in the web UI against what was commanded.
- **คำอธิบายภาษาไทย**: สมมติว่าความเร็วแปรตาม duty เพื่อประมาณแบบวงเปิด โหลดและแรงเสียดทานทำให้ต่างจากค่าจริงได้
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Engineering Caveat / ข้อควรระวัง**: Open loop means load changes the real speed. The encoder reading is the truth; this is the request.
- **Implementation Code Location**:
  * `firmware/src/modules/lift/LiftModule.cpp` (Line 31): *maxMms() and estMms()*
  * `firmware/src/modules/lift/LiftModule.h` (Line 34): *the mapping, in a comment*
- **Supporting References**:
  * `[6]` KHK Gears (n.d.) — *Calculation of Gear Dimensions* ([Link](https://khkgears.net/new/gear_knowledge/gear_technical_reference/calculation_gear_dimensions.html))
  * `[5]` K. J. Åström and R. M. Murray (2008) — *Feedback Systems: An Introduction for Scientists and Engineers* ([Link](https://authors.library.caltech.edu/records/yzs24-xsx88))

---

### Card: Encoder counts to millimetres (แปลงจำนวนพัลส์เอนโคเดอร์เป็นระยะ)
- **ID**: `counts-mm` | **Group**: *Lift — rack and pinion* | **Status**: `IMPLEMENTED`

```text
counts per mm = counts_per_rev &divide; mm_per_rev
```

- **English Description**: counts_per_rev is counted at the PINION, so it already includes the gearbox ratio (encoder counts/rev &times; gearbox). Getting that wrong scales every position and every measured speed by the same factor, which reads as a mechanical fault and is not one.
- **คำอธิบายภาษาไทย**: ต้องระบุว่า counts ต่อรอบรวมการนับขอบและอัตราทดแล้วหรือยัง เพื่อไม่คูณซ้ำ
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Implementation Code Location**:
  * `firmware/src/modules/lift/LiftModule.cpp` (Line 27): *cpm()*
- **Supporting References**:
  * `[18]` PJRC (n.d.) — *Encoder Library* ([Link](https://www.pjrc.com/teensy/td_libs_Encoder.html))
  * `[6]` KHK Gears (n.d.) — *Calculation of Gear Dimensions* ([Link](https://khkgears.net/new/gear_knowledge/gear_technical_reference/calculation_gear_dimensions.html))

---

### Card: Holding a position (PID + feed-forward) (PID พร้อม feed-forward และตัวกรอง)
- **ID**: `pid` | **Group**: *Lift — rack and pinion* | **Status**: `IMPLEMENTED`

```text
I_k = clamp(I_(k-1) + e_k Δt, I_min, I_max)
D_raw = (e_k - e_(k-1)) / Δt
α = exp(-2π f_c Δt); D_k = αD_(k-1) + (1-α)D_raw
u_k = clamp(Kp e_k + Ki I_k + Kd D_k + Kf r_k, u_min, u_max)
```

- **English Description**: The derivative of a quantised encoder is mostly noise, so it is passed through a one-pole low-pass with a cut-off in Hz — a time constant a person can reason about, instead of a bare smoothing constant. The integral is clamped, and inside the deadband it is reset so the term cannot wind up while the lift is parked.
- **คำอธิบายภาษาไทย**: สมการในโค้ดเป็นเวลาไม่ต่อเนื่อง มีการจำกัดอินทิกรัลและเอาต์พุต ค่าจูนต้องรายงานจากการทดลอง
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Implementation Code Location**:
  * `firmware/lib/PIDF/PIDF.cpp` (Line 60): *compute_with_error()*
  * `firmware/lib/PIDF/PIDF.cpp` (Line 87): *the derivative low-pass*
- **Supporting References**:
  * `[5]` K. J. Åström and R. M. Murray (2008) — *Feedback Systems: An Introduction for Scientists and Engineers* ([Link](https://authors.library.caltech.edu/records/yzs24-xsx88))
  * `[8]` S. W. Smith (n.d.) — *The Scientist and Engineer’s Guide to Digital Signal Processing: Single Pole Recursive Filters* ([Link](https://www.dspguide.com/ch19/2.htm))
  * `[110]` S. Panaudomsup, T. Subhagandha, K. Chanma, and S. Boksuwan (2025) — *Developing HERMS Temperature Control: A Study on PID-P and PI-P Cascade Control* ([Link](https://doi.org/10.1109/ecti-con64996.2025.11101691))
  * `[126]` N. Kongchoo, P. Santiprapan, and N. Jindapetch (2022) — *Mathematical Model and PI Controller Design Based on Indirect Vector Control for Permanent Magnet Synchronous Motor* ([Link](https://doi.org/10.37936/ecti-cit.2022163.245351))
  * `[133]` P. Sutyasadi, M. Wicaksono, and D. Maneetham (2023) — *Improvement Control of a Three Axis Articulated Robotic Arm Using PID Cascade Control* ([Link](https://doi.org/10.1109/citsm60085.2023.10455548))

---

### Card: When each board answers a broadcast PING (ช่วงเวลาตอบกลับบนบัส RS485)
- **ID**: `rs485-slot` | **Group**: *How the boards talk* | **Status**: `IMPLEMENTED`

```text
scheduled delay = (id mod 24) × 10 ms; range 0…230 ms
8N1 payload transmission time = 10N / baud seconds
```

- **English Description**: The code staggers discovery replies using a bounded modulo schedule. A 30-byte reply at 115200 baud takes approximately 2.60 ms before additional delimiters or processing. Scheduling delay does not guarantee every response is received within 240 ms.
- **คำอธิบายภาษาไทย**: การเลือกสล็อตด้วย id modulo 24 เป็นวิธีของโครงการ ไม่ใช่ Modbus และอุปกรณ์ที่ได้สล็อตเดียวกันยังชนกันได้
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Engineering Caveat / ข้อควรระวัง**: IDs separated by multiples of 24 share a slot. Collisions, queued work and transport delay remain possible; addressed follow-up and actual bus measurements are needed. Modbus timing is related comparison only; Mice does not use its RTU framing.
- **Implementation Code Location**:
  * `firmware/src/core/RS485Bus.cpp` (Line 95): *the staggered reply slot*
- **Supporting References**:
  * `[10]` T. Kugelstadt (2021) — *The RS-485 Design Guide* ([Link](https://www.ti.com/lit/an/slla272d/slla272d.pdf))
  * `[13]` Espressif Systems (v4.4.7) — *ESP-IDF Programming Guide: Universal Asynchronous Receiver/Transmitter (UART)* ([Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/peripherals/uart.html))

---

### Card: When a module leaves the show network for a neighbour (ฮิสเทอรีซิสของการเปลี่ยนเครือข่าย)
- **ID**: `wifi-roam` | **Group**: *How the boards talk* | **Status**: `IMPLEMENTED`

```text
WEAK_RSSI = -78 dBm; GOOD_RSSI = -67 dBm; MARGIN = 12 dB
hysteresis width = GOOD_RSSI - WEAK_RSSI = 11 dB
```

- **English Description**: WifiLink implements an application-level policy with separate leave/return thresholds and a required improvement for a candidate relay. These numbers are project choices, not universal RF quality guarantees.
- **คำอธิบายภาษาไทย**: เกณฑ์ RSSI และส่วนต่างสัญญาณเป็นค่าตั้งของโครงการ ไม่ใช่ค่าเกณฑ์บังคับของ IEEE 802.11k/r
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Engineering Caveat / ข้อควรระวัง**: A scan/reconnect policy is not evidence of implementing IEEE 802.11k neighbor reports or 802.11r fast transition. Preserve the exact conditions in choose().
- **Implementation Code Location**:
  * `firmware/src/core/WifiLink.h` (Line 35): *GOOD_RSSI and WEAK_RSSI*
- **Supporting References**:
  * `[15]` Espressif Systems (v4.4.7) — *ESP-IDF Programming Guide: Wi-Fi* ([Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/network/esp_wifi.html))
  * `[5]` K. J. Åström and R. M. Murray (2008) — *Feedback Systems: An Introduction for Scientists and Engineers* ([Link](https://authors.library.caltech.edu/records/yzs24-xsx88))

---

### Card: Driving an analog amplifier from a digital pin (กรองสัญญาณหนึ่งบิตเป็นเสียงอนาล็อก)
- **ID**: `analog-audio` | **Group**: *Sound* | **Status**: `IMPLEMENTED`

```text
1-bit delta-sigma output → RC low-pass → analog amplifier
f_c = 1/(2πRC); R = 1000 Ω, C = 100 nF ⇒ f_c ≈ 1591.55 Hz
```

- **English Description**: A TPA3118, TPA3110 or PAM8403 is an ANALOG class-D amp: its input is a line signal. Fed raw I2S bits it plays loud noise, not sound. The delta-sigma stream carries the waveform in its density, and the RC filter averages it back into a voltage.
- **คำอธิบายภาษาไทย**: วงจร RC เป็นแบบจำลองอันดับหนึ่ง ค่า R และ C ต้องตรวจบนวงจรจริง ไม่ควรต่อ I2S เข้าขยายเสียงอนาล็อกโดยตรง
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Engineering Caveat / ข้อควรระวัง**: The RC value is an ideal unloaded example, not a claim about an installed filter or full-band audio fidelity. Amplifier impedance and output loading modify the response.
- **Implementation Code Location**:
  * `firmware/src/core/AudioPlayer.cpp` (Line 30): *the analog branch of begin()*
  * `firmware/config/amps.json` (Line 1): *which amp each board has — the list itself*
- **Supporting References**:
  * `[30]` E. F. Philhower III and contributors (n.d.) — *ESP8266Audio* ([Link](https://github.com/earlephilhower/ESP8266Audio))
  * `[29]` Texas Instruments (n.d.) — *TPA3118D2: 30-W stereo, 60-W mono, 4.5-V to 26-V supply, analog-input Class-D audio amplifier* ([Link](https://www.ti.com/product/TPA3118D2))
  * `[8]` S. W. Smith (n.d.) — *The Scientist and Engineer’s Guide to Digital Signal Processing: Single Pole Recursive Filters* ([Link](https://www.dspguide.com/ch19/2.htm))

---

### Card: Servo presets (ค่าตั้งเซอร์โวแต่ละรุ่น)
- **ID**: `servo-presets` | **Group**: *Hardware, as data* | **Status**: `IMPLEMENTED`

```text
one entry = label, travel (180&deg; or 270&deg;), pulse range, max &deg;/s
```

- **English Description**: The servo registry stores configurable pulse endpoints, travel, speed and gearing. Cite the manufacturer for verified product properties and the registry plus calibration record for project values. A generic MG90S listing does not validate every clone, PDI-1181MG, or TianKongRC configuration.
- **คำอธิบายภาษาไทย**: ข้อมูลผู้ผลิตรองรับเฉพาะรุ่นที่ระบุ ช่วงพัลส์และมุมของ PDI/TianKongRC ในโครงการยังต้องยืนยันด้วยเอกสารรุ่นจริงหรือการวัด
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Engineering Caveat / ข้อควรระวัง**: range is the SERVO's own travel, never the joint's limits. Mixing the two sends the arm to the wrong angle with nothing to show for it.
- **Implementation Code Location**:
  * `firmware/config/servos.json` (Line 1): *every servo this project knows*
- **Supporting References**:
  * `[16]` Tower Pro (n.d.) — *MG90S* ([Link](https://towerpro.com.tw/product/mg90s-3/))
  * `[17]` ESP32Servo contributors (n.d.) — *ESP32Servo* ([Link](https://github.com/madhephaestus/ESP32Servo))

---

### Card: Camera board pin maps (การกำหนดขากล้องแต่ละบอร์ด)
- **ID**: `cam-boards` | **Group**: *Hardware, as data* | **Status**: `IMPLEMENTED`

```text
one entry = the board's own pin map; the firmware table and the hub's pin diagram are both GENERATED from it
```

- **English Description**: The map used to be a table inside CamModule.cpp with the drawing kept separately, so the two could disagree. Now a board added here arrives complete with its own diagram, and the diagram cannot contradict the wiring the firmware compiled.
- **คำอธิบายภาษาไทย**: อ้างอิงไดรเวอร์และข้อมูลไมโครคอนโทรลเลอร์ แต่ต้องตรวจผังขาของบอร์ดที่ติดตั้งจริง
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Engineering Caveat / ข้อควรระวัง**: A board entered wrongly is a camera that initialises and returns noise, so the generator refuses a missing pin or a GPIO that does not exist, and says which.
- **Implementation Code Location**:
  * `firmware/config/cam_boards.json` (Line 1): *ai-thinker, esp-eye, m5stack, m5stack-wide, ttgo-journal*
- **Supporting References**:
  * `[31]` Espressif Systems (n.d.) — *esp32-camera* ([Link](https://github.com/espressif/esp32-camera))
  * `[12]` Espressif Systems (n.d.) — *ESP32 Series Datasheet* ([Link](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf))

---

### Card: Angle wrap / normalize (radians & degrees) (ทำให้มุมอยู่ในช่วงที่กำหนด)
- **ID**: `angle-wrap` | **Group**: *Math utilities* | **Status**: `IMPLEMENTED`

```text
WrapDegs(x): subtract/add 360 once only if x &gt; 180 or x &lt; -180
NormalizeDegs(x): fmod(x,360)
Radian helpers use π and 2π in the same pattern
```

- **English Description**: These are actual helper definitions, not a complete modulo normalization for arbitrary inputs. WrapDegs(1080) returns 720; NormalizeDegs(-10) remains -10. Production use in IMU fusion or PID was not established by this audit.
- **คำอธิบายภาษาไทย**: ฟังก์ชันในไฟล์ปรับเพียงหนึ่งรอบ จึงไม่ได้ทำให้ทุกค่าอยู่ในช่วงมาตรฐาน เช่น WrapDegs(1080) ได้ 720 และ NormalizeDegs(-10) ยังเป็น -10 การมีฟังก์ชันไม่ได้ยืนยันว่าทุกระบบเรียกใช้
- **Units & Variables**: x: degrees for Degs, radians for Rads
- **Engineering Caveat / ข้อควรระวัง**: Code was documented, not changed. A full normalization would require a different implementation and separate runtime review.
- **Implementation Code Location**:
  * `firmware/lib/Utilize/Utilize.h` (Line 20): *WrapRads(), WrapDegs(), NormalizeRads(), NormalizeDegs()*
- **Supporting References**:
  * `[9]` BIPM (2019) — *The International System of Units (SI), SI Brochure* ([Link](https://www.bipm.org/en/publications/si-brochure))
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))

---

### Card: Radians ↔ Degrees conversion (แปลงเรเดียนกับองศา)
- **ID**: `angle-convert` | **Group**: *Math utilities* | **Status**: `IMPLEMENTED`

```text
deg = rad × 180/π    (ToDegrees)
rad = deg × π/180    (ToRadians)
```

- **English Description**: Trig functions (sin, cos, atan2) work in radians; servo pulses, pose files, and human-readable config use degrees. Every boundary crossing converts explicitly.
- **คำอธิบายภาษาไทย**: หนึ่งรอบเท่ากับ 2π เรเดียนและ 360 องศา ชนิดหน่วยของฟังก์ชันต้องดูจาก API ไม่ใช่มาตรฐานเลขลอยตัว
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Implementation Code Location**:
  * `firmware/lib/Utilize/Utilize.h` (Line 8): *ToDegrees(), ToRadians()*
- **Supporting References**:
  * `[9]` BIPM (2019) — *The International System of Units (SI), SI Brochure* ([Link](https://www.bipm.org/en/publications/si-brochure))

---

### Card: At-target check (range / angle tolerance) (ตัดสินว่าถึงเป้าหมายหรือยัง)
- **ID**: `at-target` | **Group**: *Math utilities* | **Status**: `IMPLEMENTED`

```text
AtTargetRange:  |number - target| < range
AtTargetAngle:  |WrapDegs(target - current)| ≤ tolerance
```

- **English Description**: The scalar helper uses strict endpoints; the angle helper uses an inclusive tolerance and the one-turn WrapDegs behavior. These definitions do not establish that limit switches, move completion or every PID path calls them.
- **คำอธิบายภาษาไทย**: การตรวจช่วงสเกลาร์ไม่รวมขอบ ส่วนการตรวจมุมรวมขอบค่าคลาดเคลื่อน ต้องระวังข้อจำกัดการปรับมุมเพียงหนึ่งรอบและตรวจจุดเรียกใช้จริง
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Implementation Code Location**:
  * `firmware/lib/Utilize/Utilize.h` (Line 16): *AtTargetRange(), AtTargetAngle()*
- **Supporting References**:
  * `[5]` K. J. Åström and R. M. Murray (2008) — *Feedback Systems: An Introduction for Scientists and Engineers* ([Link](https://authors.library.caltech.edu/records/yzs24-xsx88))

---

### Card: Linear speed → RPM (wheel / rack) (แปลงความเร็วเชิงเส้นเป็นรอบต่อนาที)
- **ID**: `mps-to-rpm` | **Group**: *Math utilities* | **Status**: `IMPLEMENTED`

```text
RPM = (m/s × 60) / (π × diameter)
```

- **English Description**: Converts linear velocity (m/s) to rotational speed (RPM) for a wheel or pinion of given diameter. Used in lift speed calibration and any wheel-driven module.
- **คำอธิบายภาษาไทย**: ใช้ความสัมพันธ์ของความเร็วสัมผัสที่วงกลมพิตช์และแปลงวินาทีเป็นนาที
- **Units & Variables**: Use the units shown in the equation and current configuration.
- **Implementation Code Location**:
  * `firmware/lib/Utilize/Utilize.h` (Line 54): *MPSToRPM()*
- **Supporting References**:
  * `[6]` KHK Gears (n.d.) — *Calculation of Gear Dimensions* ([Link](https://khkgears.net/new/gear_knowledge/gear_technical_reference/calculation_gear_dimensions.html))
  * `[9]` BIPM (2019) — *The International System of Units (SI), SI Brochure* ([Link](https://www.bipm.org/en/publications/si-brochure))

---

### Card: Sign of a number (−1, 0, +1) (ฟังก์ชันเครื่องหมาย)
- **ID**: `sig-num` | **Group**: *Math utilities* | **Status**: `IMPLEMENTED`

```text
Mathematical sign(x): -1, 0, +1
Actual SigNum() returns Arduino byte: negative x → 255; zero → 0; positive → 1
```

- **English Description**: The helper casts the conditional result to an unsigned byte. It therefore does not return mathematical -1 for a negative finite input. This is a code-level discrepancy; no motor-direction usage is inferred.
- **คำอธิบายภาษาไทย**: ฟังก์ชันแปลงผลเป็น byte แบบไม่มีเครื่องหมาย ค่า -1 จึงกลายเป็น 255 ไม่ใช่ฟังก์ชันเครื่องหมายทางคณิตศาสตร์ตามคำอธิบายเดิม การอ้างอิงนี้ไม่ได้แก้โค้ดควบคุม
- **Units & Variables**: Input: numeric; output: unsigned 8-bit integer
- **Engineering Caveat / ข้อควรระวัง**: Confirm intended callers before changing the return type. Non-finite inputs need their own policy.
- **Implementation Code Location**:
  * `firmware/lib/Utilize/Utilize.h` (Line 50): *SigNum()*
- **Supporting References**:
  * `[101]` ISO/IEC JTC1/SC22/WG21 (n.d.) — *C++ working draft: Integral conversions* ([Link](https://eel.is/c++draft/conv.integral))

---

### Card: Forward kinematics: elbow / wrist XYZ from joint angles (คำนวณตำแหน่งข้อศอกและข้อมือ)
- **ID**: `fk-arm` | **Group**: *Nong — the humanoid* | **Status**: `IMPLEMENTED`

```text
Module page: R_s = R_x(a0) R_z(a1); R_e = R_s R_x(a2) R_z(a3)
p_elbow = p_shoulder + R_s [0,-115,0]ᵀ
p_wrist = p_elbow + R_e [0,-105,0]ᵀ; p_shoulder=[±105,95,0] mm
Display body step: y_new=y+x sin(shrug); then yaw x,z about Y
```

- **English Description**: fkArm() on the module page uses fixed dimensions and joint direction signs. Its shrug display step is a shear-like visual approximation, not a full rigid rotation. It is an estimate from commanded/reported joint values, not measured Cartesian position.
- **คำอธิบายภาษาไทย**: หน้าโมดูลใช้ความยาวคงที่และทิศหมุนที่ระบุใน fkArm ส่วนการยกไหล่เป็นการประมาณภาพ ไม่ใช่เมทริกซ์หมุนวัตถุแข็งครบถ้วน ค่าพิกัดเป็นผลคำนวณจากมุม ไม่ใช่การวัดตำแหน่งจริง
- **Units & Variables**: Angles a_i: rad after direction/90° offset; positions: mm
- **Engineering Caveat / ข้อควรระวัง**: Does not match every configurable Studio rig: Studio default shoulder ±120/110 mm, upper 110 mm, forearm 130 mm, configurable axes/tilts and shrug calibration. Do not combine the two geometry models in one experimental result.
- **Implementation Code Location**:
  * `firmware/src/web/WebUI.h` (Line 834): *fkArm() — fixed module-page geometry*
  * `firmware/src/web/WebUI.h` (Line 849): *renderNong() — approximate body display*
- **Supporting References**:
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))
  * `[54]` Three.js contributors (n.d.) — *Three.js documentation* ([Link](https://threejs.org/docs/))
  * `[4]` J. Denavit and R. S. Hartenberg (1955) — *A Kinematic Notation for Lower-Pair Mechanisms Based on Matrices* ([Link](https://doi.org/10.1115/1.4011045))
  * `[105]` P. Uthong and V. Sangveraphunsiri (2015) — *Dexterity Measure for a 2-DOF Revolute Spherical Serial Manipulator* ([Link](https://doi.org/10.4028/www.scientific.net/amm.799-800.1016))
  * `[119]` S. Nakdhamabhorn, M. B. Pillai, and J. Suthakorn (2021) — *Design and development of sensorless based 5-DOF bilaterally controlled surgical manipulator: A prototype* ([Link](https://doi.org/10.11591/eei.v10i2.2331))
  * `[127]` J. Chaichawananit and S. Saiyod (2016) — *Solving inverse kinematics problem of robot arm based on a-star algorithm* ([Link](https://doi.org/10.1109/jcsse.2016.7748846))
  * `[137]` D. E. Whitney (1969) — *Resolved Motion Rate Control of Manipulators and Human Prostheses* ([Link](https://doi.org/10.1109/tmms.1969.299896))

---

### Card: Cosine velocity, acceleration and duration limits (ความเร็วและความเร่งสูงสุดของเส้นโคไซน์)
- **ID**: `cosine-limits` | **Group**: *Nong — the humanoid* | **Status**: `DERIVED`

```text
q(t)=q0+Δq[1-cos(πt/T)]/2
v(t)=Δq π sin(πt/T)/(2T)
a(t)=Δq π² cos(πt/T)/(2T²)
T ≥ max_i(π|Δq_i|/(2v_limit_i), sqrt(π²|Δq_i|/(2a_limit_i)))
```

- **English Description**: Differentiate the implemented cosine position law with respect to physical time. These are peak constraints for this particular profile, assuming specified joint-space limits. They are not implemented by the existing average-speed duration rule.
- **คำอธิบายภาษาไทย**: หาอนุพันธ์จากสมการตำแหน่งจริง เพื่อใช้ตรวจข้อจำกัดความเร็วและความเร่ง สูตรนี้เป็นการอนุมาน ไม่ใช่ผลทดลองหรือข้อจำกัดที่โค้ดบังคับแล้ว
- **Units & Variables**: Δq: deg or rad consistently; T: s; v_limit: angle/s; a_limit: angle/s²
- **Engineering Caveat / ข้อควรระวัง**: Derived bounds for a cosine segment with positive limits; firmware minDuration() does not implement this peak-velocity/acceleration bound. At stationary joins, acceleration jumps.
- **Implementation Code Location**:
  * `firmware/src/modules/nong/NongMath.h` (Line 98): *inline float ease*
- **Supporting References**:
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))
  * `[72]` Luigi Biagiotti and Claudio Melchiorri (2009) — *Trajectory Planning for Automatic Machines and Robots* ([Link](https://link.springer.com/book/10.1007/978-3-540-85629-0))
  * `[123]` N. Ajjanaromvat and M. Parnichkun (2018) — *Trajectory tracking using online learning LQR with adaptive learning control of a leg-exoskeleton for disorder gait rehabilitation* ([Link](https://doi.org/10.1016/j.mechatronics.2018.03.003))

---

### Card: Damped least-squares inverse kinematics (จลนศาสตร์ผกผันแบบ DLS)
- **ID**: `dls-ik` | **Group**: *Nong — the humanoid* | **Status**: `IMPLEMENTED`

```text
e = p_target - p(q)
J[:,j] ≈ [p(q + ε e_j) - p(q)] / ε
Δq = Jᵀ (JJᵀ + λ²I)^(-1) e
```

- **English Description**: solveIK() constructs a finite-difference 3×4 positional Jacobian and solves a damped system, then clamps joint changes. EPS=0.6 degrees and LAMBDA2=4 are project tuning values.
- **คำอธิบายภาษาไทย**: โค้ดคำนวณ Jacobian เชิงตัวเลขแล้วเพิ่ม damping เพื่อลดปัญหาใกล้จุดเอกฐาน ค่าจูนและเกณฑ์หยุดต้องรายงานแยกจากทฤษฎี
- **Units & Variables**: Defined beside each symbol in the equation.
- **Engineering Caveat / ข้อควรระวัง**: Convergence and collision avoidance are not guaranteed by this update. Jacobian units are mm/degree in this implementation.
- **Implementation Code Location**:
  * `nong/main_python_set_nong/web/app.js` (Line 1119): *function solveIK(*
- **Supporting References**:
  * `[3]` C. W. Wampler (1986) — *Manipulator Inverse Kinematic Solutions Based on Vector Formulations and Damped Least-Squares Methods* ([Link](https://doi.org/10.1109/TSMC.1986.289285))
  * `[2]` S. R. Buss (2009) — *Introduction to Inverse Kinematics with Jacobian Transpose, Pseudoinverse and Damped Least Squares Methods* ([Link](https://math.ucsd.edu/~sbuss/ResearchWeb/ikmethods/iksurvey.pdf))
  * `[74]` A. A. Maciejewski and C. A. Klein (1988) — *Numerical filtering for the operation of robotic manipulators through kinematically singular configurations* ([Link](https://onlinelibrary.wiley.com/doi/abs/10.1002/rob.4620050603))
  * `[75]` Y. Nakamura and H. Hanafusa (1986) — *Inverse Kinematic Solutions With Singularity Robustness for Robot Manipulator Control* ([Link](https://asmedigitalcollection.asme.org/dynamicsystems/article-abstract/108/3/163/409605/))
  * `[105]` P. Uthong and V. Sangveraphunsiri (2015) — *Dexterity Measure for a 2-DOF Revolute Spherical Serial Manipulator* ([Link](https://doi.org/10.4028/www.scientific.net/amm.799-800.1016))
  * `[119]` S. Nakdhamabhorn, M. B. Pillai, and J. Suthakorn (2021) — *Design and development of sensorless based 5-DOF bilaterally controlled surgical manipulator: A prototype* ([Link](https://doi.org/10.11591/eei.v10i2.2331))
  * `[127]` J. Chaichawananit and S. Saiyod (2016) — *Solving inverse kinematics problem of robot arm based on a-star algorithm* ([Link](https://doi.org/10.1109/jcsse.2016.7748846))
  * `[137]` D. E. Whitney (1969) — *Resolved Motion Rate Control of Manipulators and Human Prostheses* ([Link](https://doi.org/10.1109/tmms.1969.299896))

---

### Card: Coordinate-descent IK refinement (ปรับคำตอบ IK ทีละข้อต่อ)
- **ID**: `ccd-ik` | **Group**: *Nong — the humanoid* | **Status**: `IMPLEMENTED`

```text
choose a feasible trial q_j that decreases ||p(q)-p_target||₂; repeat
```

- **English Description**: ccdChain() tries finite joint changes and retains improvements after DLS. Cite numerical IK background, but describe the actual finite-step search rather than claiming a closed-form CCD rotation update.
- **คำอธิบายภาษาไทย**: เป็นการลองปรับมุมทีละตัวแล้วเก็บค่าที่ลดความคลาดเคลื่อน อาจติดค่าต่ำสุดเฉพาะที่และไม่ได้รับประกันว่าถึงทุกเป้าหมาย
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `nong/main_python_set_nong/web/app.js` (Line 1169): *function ccdChain(*
- **Supporting References**:
  * `[2]` S. R. Buss (2009) — *Introduction to Inverse Kinematics with Jacobian Transpose, Pseudoinverse and Damped Least Squares Methods* ([Link](https://math.ucsd.edu/~sbuss/ResearchWeb/ikmethods/iksurvey.pdf))
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))

---

### Card: Perspective versus orthographic view (มุมมอง perspective และ orthographic)
- **ID**: `camera-view` | **Group**: *Studio and operator interface* | **Status**: `IMPLEMENTED`

```text
visible height = 2d tan(FOV_y/2)
T_world = T_parent T_local
```

- **English Description**: The editor computes an orthographic scale from the perspective camera distance and uses hierarchical transforms for its robot. This is rendering geometry; it is not calibration of the ESP32 camera.
- **คำอธิบายภาษาไทย**: ใช้รักษาขนาดมุมมองเมื่อสลับกล้องในโปรแกรมจำลอง ไม่ใช่การสอบเทียบกล้องจริง
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `nong/main_python_set_nong/web/app.js` (Line 530): *const h = 2 * dist*
- **Supporting References**:
  * `[54]` Three.js contributors (n.d.) — *Three.js documentation* ([Link](https://threejs.org/docs/))
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))
  * `[113]` P. Bamrungthai and V. Sangveraphunsiri (2013) — *A Multi-Camera System for Mobile Robot Localization and Calibration* ([Link](https://doi.org/10.2316/p.2013.799-107))
  * `[130]` U. Suttapakti and A. Bunpeng (2021) — *Adaptive Kernel Transform for Face Recognition Under Uneven Illumination Conditions* ([Link](https://doi.org/10.1109/icsec53205.2021.9684605))
  * `[132]` P. Nattharith and M. Güzel (2016) — *Machine vision and fuzzy logic-based navigation control of a goal-oriented mobile robot* ([Link](https://doi.org/10.1177/1059712316645845))
  * `[134]` L. Villaverde, D. Maneetham, and T. Rabgyal (2022) — *Camera Calibration Algorithm for Industrial Robot* ([Link](https://doi.org/10.1109/itis57155.2022.10009991))
  * `[136]` N. Otanasap and P. Boonbrahm (2017) — *Pre-impact fall detection system using dynamic threshold and 3D bounding box* ([Link](https://doi.org/10.1117/12.2266822))
  * `[140]` R. Y. Tsai (1987) — *A versatile camera calibration technique for high-accuracy 3D machine vision metrology using off-the-shelf TV cameras and lenses* ([Link](https://doi.org/10.1109/jra.1987.1087109))
  * `[142]` D. G. Lowe (2004) — *Distinctive Image Features from Scale-Invariant Keypoints* ([Link](https://doi.org/10.1023/b:visi.0000029664.99615.94))

---

### Card: PWM duty, frequency and resolution (ความถี่ PWM และความละเอียด duty)
- **ID**: `pwm-duty` | **Group**: *Embedded hardware* | **Status**: `IMPLEMENTED`

```text
T_pwm = 1/f_pwm; duty = t_high/T_pwm
approximate time step = T_pwm / 2^b
```

- **English Description**: The LEDC timer and servo library convert configured pulses to timer duty. Frequency, timer resolution and pulse range must be considered together.
- **คำอธิบายภาษาไทย**: เวลาต่อหนึ่งขั้นขึ้นกับความถี่และจำนวนบิต ค่าที่ใช้ควรอ้างอิงการตั้ง timer จริงและข้อจำกัดเซอร์โว
- **Units & Variables**: f: Hz; T,t_high: seconds; b: timer bits.
- **Engineering Caveat / ข้อควรระวัง**: Resolution of the generated pulse is not the servo mechanical resolution or internal deadband. Measure the actual pulse-to-angle response under load.
- **Implementation Code Location**:
  * `firmware/src/modules/nong/NongModule.cpp` (Line 302): *writeMicroseconds*
- **Supporting References**:
  * `[14]` Espressif Systems (v4.4.7) — *ESP-IDF Programming Guide: LED Control (LEDC)* ([Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/peripherals/ledc.html))
  * `[17]` ESP32Servo contributors (n.d.) — *ESP32Servo* ([Link](https://github.com/madhephaestus/ESP32Servo))
  * `[102]` J. Malášek (Pololu) (2011) — *Electrical characteristics of servos and introduction to the servo control interface* ([Link](https://www.pololu.com/blog/16/electrical-characteristics-of-servos-and-introduction-to-the-servo-control-interface))

---

### Card: Servo power and torque sizing (งบกระแสไฟและแรงบิด)
- **ID**: `power-budget` | **Group**: *Embedded hardware* | **Status**: `EVALUATION`

```text
P = VI; τ_load = F r; F_gravity = mg
τ_joint,ideal = τ_servo × gear/pinion
```

- **English Description**: Use manufacturer ratings as input to a design estimate, with efficiency and operating margins. Rated stall torque does not mean continuous safe torque, and combined transient current must be measured.
- **คำอธิบายภาษาไทย**: แยกแรงบิดหยุดหมุนออกจากแรงบิดใช้งานต่อเนื่อง ต้องวัดกระแสหลายเซอร์โวพร้อมกัน แรงบิดและระยะแขนจริง
- **Units & Variables**: P: W; V: V; I: A; τ: N·m; F: N; r: m; m: kg.
- **Engineering Caveat / ข้อควรระวัง**: No complete electrical or structural safety certification is established by this estimate.
- **Implementation Code Location**:
  * `firmware/config/servos.json` (Line 1): *Configured servo ratings; sizing context*
- **Supporting References**:
  * `[16]` Tower Pro (n.d.) — *MG90S* ([Link](https://towerpro.com.tw/product/mg90s-3/))
  * `[6]` KHK Gears (n.d.) — *Calculation of Gear Dimensions* ([Link](https://khkgears.net/new/gear_knowledge/gear_technical_reference/calculation_gear_dimensions.html))
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))
  * `[12]` Espressif Systems (n.d.) — *ESP32 Series Datasheet* ([Link](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf))

---

### Card: RS485 electrical design and line loading (การออกแบบสายและโหลด RS485)
- **ID**: `rs485-electrical` | **Group**: *Communication and discovery* | **Status**: `EVALUATION`

```text
V_diff = V_A - V_B; Γ = (Z_L - Z_0)/(Z_L + Z_0)
ideal matched termination: Z_L = Z_0
```

- **English Description**: The reflection coefficient is transmission-line background for termination. Use the TI guide for topology and biasing and the actual transceiver datasheet for electrical limits.
- **คำอธิบายภาษาไทย**: การแมตช์อิมพีแดนซ์ช่วยลดการสะท้อน ต้องตรวจตำแหน่งตัวต้านทาน ปลายสาย สายกิ่ง และกราวด์จริง
- **Units & Variables**: Defined beside each symbol in the equation.
- **Engineering Caveat / ข้อควรระวัง**: The Mice ASCII command protocol is custom; RS485 is only its electrical transport.
- **Implementation Code Location**:
  * `firmware/src/core/RS485Bus.cpp` (Line 14): *Serial2*
- **Supporting References**:
  * `[10]` T. Kugelstadt (2021) — *The RS-485 Design Guide* ([Link](https://www.ti.com/lit/an/slla272d/slla272d.pdf))
  * `[11]` Maxim Integrated / Analog Devices (n.d.) — *MAX1487–MAX491: Low-Power, Slew-Rate-Limited RS-485/RS-422 Transceivers* ([Link](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX1487-MAX491.pdf))

---

### Card: HTTP command and file APIs (API คำสั่งและไฟล์ผ่าน HTTP)
- **ID**: `http-api` | **Group**: *Communication and discovery* | **Status**: `IMPLEMENTED`

```text
request(method, target, body) → response(status, representation)
```

- **English Description**: Map control actions, authentication failures and file transfers to the actual routes. HTTP semantics supports the protocol explanation, while Mice defines its route names and data schemas.
- **คำอธิบายภาษาไทย**: อ้าง RFC เพื่ออธิบาย HTTP แล้วอ้างซอร์สโค้ดสำหรับ endpoint และ schema ของโครงการ
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `firmware/src/core/WebPortal.cpp` (Line 150): *setupRoutes*
  * `main_python/main.py` (Line 3519): *def do_GET*
- **Supporting References**:
  * `[19]` R. Fielding, M. Nottingham and J. Reschke, Eds. (2022) — *HTTP Semantics* ([Link](https://www.rfc-editor.org/rfc/rfc9110.html))
  * `[23]` T. Bray, Ed. (2017) — *The JavaScript Object Notation (JSON) Data Interchange Format* ([Link](https://www.rfc-editor.org/rfc/rfc8259.html))

---

### Card: WebSocket handshake and event framing (การเชื่อมต่อและรับเหตุการณ์ WebSocket)
- **ID**: `websocket-feed` | **Group**: *Face integration* | **Status**: `IMPLEMENTED`

```text
Sec-WebSocket-Accept = Base64(SHA1(key + GUID))
client payload byte_i XOR mask_(i mod 4)
```

- **English Description**: The local face adapter implements handshake verification and frame processing. The protocol hash establishes the WebSocket handshake; it is not a password hash or message signature.
- **คำอธิบายภาษาไทย**: ใช้ RFC 6455 อธิบาย handshake และ masking ส่วนความหมายของเหตุการณ์และข้อมูลใบหน้าเป็นสัญญาของบริการภายนอก
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `apps/faces/wsclient.py` (Line 101): *hashlib.sha1*
- **Supporting References**:
  * `[20]` I. Fette and A. Melnikov (2011) — *The WebSocket Protocol* ([Link](https://www.rfc-editor.org/rfc/rfc6455.html))
  * `[24]` S. Josefsson (2006) — *The Base16, Base32, and Base64 Data Encodings* ([Link](https://www.rfc-editor.org/rfc/rfc4648.html))

---

### Card: Local name and service discovery (การค้นหาชื่อและบริการในเครือข่าย)
- **ID**: `local-discovery` | **Group**: *Communication and discovery* | **Status**: `IMPLEMENTED`

```text
mDNS: local-link name resolution; DNS-SD: service instances
```

- **English Description**: Separate multicast name/service discovery from address scanning and RS485 discovery. Cite the RFC only for the path actually used; project fallbacks are application behavior.
- **คำอธิบายภาษาไทย**: ควรแยกการค้นหาด้วยชื่อออกจากการสแกน IP และบัส RS485 ไม่ควรเรียกรวมว่าเป็นอัลกอริทึมเดียว
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `firmware/src/core/PeerDiscovery.cpp` (Line 1): *include*
- **Supporting References**:
  * `[21]` S. Cheshire and M. Krochmal (2013) — *Multicast DNS* ([Link](https://www.rfc-editor.org/rfc/rfc6762.html))
  * `[22]` S. Cheshire and M. Krochmal (2013) — *DNS-Based Service Discovery* ([Link](https://www.rfc-editor.org/rfc/rfc6763.html))
  * `[15]` Espressif Systems (v4.4.7) — *ESP-IDF Programming Guide: Wi-Fi* ([Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/network/esp_wifi.html))

---

### Card: Base64 chunk expansion (ขนาดข้อมูลเมื่อเข้ารหัส Base64)
- **ID**: `base64-transfer` | **Group**: *Firmware updates and security* | **Status**: `IMPLEMENTED`

```text
encoded_chars = 4 ceil(raw_bytes / 3)
```

- **English Description**: Firmware chunks expand before serial framing. Header bytes, delimiters and acknowledgements add further bandwidth and latency cost.
- **คำอธิบายภาษาไทย**: ใช้คำนวณงบข้อมูลส่งเฟิร์มแวร์ ต้องรวมส่วนหัว ขนาด chunk และการตอบกลับ ไม่ใช่นับเฉพาะไฟล์ไบนารี
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `firmware/src/core/BusUpdate.cpp` (Line 7): *FWDATA*
- **Supporting References**:
  * `[24]` S. Josefsson (2006) — *The Base16, Base32, and Base64 Data Encodings* ([Link](https://www.rfc-editor.org/rfc/rfc4648.html))
  * `[13]` Espressif Systems (v4.4.7) — *ESP-IDF Programming Guide: Universal Asynchronous Receiver/Transmitter (UART)* ([Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/peripherals/uart.html))

---

### Card: Checksum versus firmware authenticity (checksum ต่างจากการยืนยันผู้สร้างเฟิร์มแวร์)
- **ID**: `firmware-integrity` | **Group**: *Firmware updates and security* | **Status**: `IMPLEMENTED`

```text
accept only if received byte count = declared count and registered MD5 check succeeds
```

- **English Description**: BusUpdate registers an MD5 value before finishing the update. This can detect accidental corruption, but an attacker able to replace image and digest is not excluded by this mechanism.
- **คำอธิบายภาษาไทย**: MD5 ไม่ใช่ลายเซ็นดิจิทัล ต้องไม่เขียนในวิทยานิพนธ์ว่าระบบป้องกันการปลอมเฟิร์มแวร์ได้จาก checksum เพียงอย่างเดียว
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `firmware/src/core/BusUpdate.cpp` (Line 46): *Update.setMD5*
- **Supporting References**:
  * `[25]` S. Turner and L. Chen (2011) — *Updated Security Considerations for the MD5 Message-Digest and the HMAC-MD5 Algorithms* ([Link](https://www.rfc-editor.org/rfc/rfc6151.html))

---

### Card: Current password storage and stronger alternatives (การเก็บรหัสผ่านปัจจุบันและแนวทางปรับปรุง)
- **ID**: `password-storage` | **Group**: *Firmware updates and security* | **Status**: `RELATED`

```text
PBKDF2(P, S, c, dkLen) → derived key (related design only)
```

- **English Description**: UserStore stores values in NVS and compares password strings. PBKDF2 is cited as a possible stronger design, not as an algorithm observed in this firmware.
- **คำอธิบายภาษาไทย**: โค้ดปัจจุบันไม่ได้แสดงการใช้ PBKDF2 จึงอ้างได้เฉพาะบททบทวนหรือแนวทางปรับปรุง ห้ามระบุว่าใช้งานแล้ว
- **Units & Variables**: Defined beside each symbol in the equation.
- **Engineering Caveat / ข้อควรระวัง**: This entry concerns firmware UserStore only. The Python hub uses salted PBKDF2; see the separate hub-password entry.
- **Implementation Code Location**:
  * `firmware/src/core/UserStore.cpp` (Line 47): *bool UserStore::verify*
- **Supporting References**:
  * `[26]` K. Moriarty, B. Kaliski and A. Rusch (2017) — *PKCS #5: Password-Based Cryptography Specification Version 2.1* ([Link](https://www.rfc-editor.org/rfc/rfc8018.html))
  * `[50]` Espressif Systems (v4.4.7) — *ESP-IDF Programming Guide: Non-volatile storage library* ([Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/storage/nvs_flash.html))

---

### Card: Tasks, locks and shared resources (งานพร้อมกันและการล็อกทรัพยากรร่วม)
- **ID**: `shared-resources` | **Group**: *Firmware and software architecture* | **Status**: `IMPLEMENTED`

```text
one active owner per serial port or shared SPI transaction
```

- **English Description**: FreeRTOS describes scheduling and synchronization primitives. The hub’s per-port ownership and SD mutex are project-level designs whose behavior must be demonstrated by concurrency tests.
- **คำอธิบายภาษาไทย**: การมี mutex ไม่ได้พิสูจน์ว่าปราศจาก race condition ต้องตรวจลำดับการล็อกและทดสอบใช้งานพร้อมกัน
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `firmware/src/core/SDStore.cpp` (Line 1): *include*
  * `firmware/src/core/PortWrite.h` (Line 1): *pragma*
- **Supporting References**:
  * `[51]` Espressif Systems (v4.4.7) — *ESP-IDF Programming Guide: FreeRTOS* ([Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/system/freertos.html))

---

### Card: Registries, generated tables and persistence (ทะเบียนข้อมูล ตารางที่สร้างอัตโนมัติ และการบันทึก)
- **ID**: `registries-storage` | **Group**: *Firmware and software architecture* | **Status**: `IMPLEMENTED`

```text
registry source → generated tables → firmware/UI consumers
```

- **English Description**: JSON and YAML define interchange syntax, while NVS and SD supply storage. The module, command, servo and app schemas are project designs, with consistency checked by QC.
- **คำอธิบายภาษาไทย**: แยกมาตรฐานรูปแบบข้อมูลออกจาก schema ที่โครงการกำหนดเอง และระบุรุ่น parser กับการทดสอบบันทึกแล้วอ่านคืน
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `firmware/tools/gen_tables.py` (Line 52): *import*
  * `tools/registry.py` (Line 18): *import*
- **Supporting References**:
  * `[23]` T. Bray, Ed. (2017) — *The JavaScript Object Notation (JSON) Data Interchange Format* ([Link](https://www.rfc-editor.org/rfc/rfc8259.html))
  * `[55]` YAML Language Development Team (2021) — *YAML Ain’t Markup Language (YAML) Version 1.2, Revision 1.2.2* ([Link](https://yaml.org/spec/1.2.2/))
  * `[50]` Espressif Systems (v4.4.7) — *ESP-IDF Programming Guide: Non-volatile storage library* ([Link](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/storage/nvs_flash.html))
  * `[56]` SD Association (n.d.) — *Simplified Specifications* ([Link](https://www.sdcard.org/downloads/pls/))

---

### Card: Camera capture and streaming bandwidth (การรับภาพและแบนด์วิดท์วิดีโอ)
- **ID**: `camera-stream` | **Group**: *Camera* | **Status**: `IMPLEMENTED`

```text
raw bitrate = width × height × bits_per_pixel × frames_per_second
compressed bitrate ≈ mean encoded frame bytes × 8 × frames_per_second
```

- **English Description**: ESP32 camera capture uses driver configuration and buffers; JPEG frame sizes depend on the scene and quality. The compressed relation is a measurement model, not a fixed compression ratio.
- **คำอธิบายภาษาไทย**: ต้องวัดขนาด JPEG และอัตราภาพจริง ไม่ควรใช้ค่าภาพดิบสรุปแบนด์วิดท์ของสตรีมบีบอัด
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `firmware/src/modules/cam/CamModule.cpp` (Line 1): *include*
  * `main_python/cam_relay.py` (Line 34): *import*
- **Supporting References**:
  * `[31]` Espressif Systems (n.d.) — *esp32-camera* ([Link](https://github.com/espressif/esp32-camera))
  * `[19]` R. Fielding, M. Nottingham and J. Reschke, Eds. (2022) — *HTTP Semantics* ([Link](https://www.rfc-editor.org/rfc/rfc9110.html))

---

### Card: Pinhole projection and lens calibration (แบบจำลองกล้องรูเข็มและการสอบเทียบเลนส์)
- **ID**: `camera-calibration` | **Group**: *Camera* | **Status**: `RELATED`

```text
s [u v 1]ᵀ = K [R | t] [X Y Z 1]ᵀ
```

- **English Description**: Use Zhang’s method and OpenCV for a future calibrated experiment. Intrinsic matrix K, distortion, coordinate frames and reprojection error must be estimated from actual images.
- **คำอธิบายภาษาไทย**: ใช้เป็นพื้นฐานบททบทวนและแผนสอบเทียบ ไม่พบหลักฐานว่าโมดูลกล้อง Mice ประมาณพารามิเตอร์เหล่านี้แล้ว
- **Units & Variables**: u,v: pixels; X,Y,Z,t: common length unit; R dimensionless.
- **Implementation Code Location**:
  * `firmware/src/modules/cam/CamModule.cpp` (Line 1): *include*
- **Supporting References**:
  * `[44]` Z. Zhang (2000) — *A Flexible New Technique for Camera Calibration* ([Link](https://doi.org/10.1109/34.888718))
  * `[43]` OpenCV contributors (4.13.0) — *Camera Calibration and 3D Reconstruction* ([Link](https://docs.opencv.org/4.13.0/d9/d0c/group__calib3d.html))
  * `[113]` P. Bamrungthai and V. Sangveraphunsiri (2013) — *A Multi-Camera System for Mobile Robot Localization and Calibration* ([Link](https://doi.org/10.2316/p.2013.799-107))
  * `[134]` L. Villaverde, D. Maneetham, and T. Rabgyal (2022) — *Camera Calibration Algorithm for Industrial Robot* ([Link](https://doi.org/10.1109/itis57155.2022.10009991))
  * `[132]` P. Nattharith and M. Güzel (2016) — *Machine vision and fuzzy logic-based navigation control of a goal-oriented mobile robot* ([Link](https://doi.org/10.1177/1059712316645845))
  * `[140]` R. Y. Tsai (1987) — *A versatile camera calibration technique for high-accuracy 3D machine vision metrology using off-the-shelf TV cameras and lenses* ([Link](https://doi.org/10.1109/jra.1987.1087109))

---

### Card: Saved-answer similarity and threshold (คะแนนจับคู่คำถามกับคำตอบที่บันทึก)
- **ID**: `voice-faq` | **Group**: *Voice and conversation* | **Status**: `IMPLEMENTED`

```text
ratio(a,b) = 2M/(len(a)+len(b))
select maximum score over stored question variants; compare with threshold
```

- **English Description**: Voice uses difflib.SequenceMatcher after stripping/lowercasing. Matching blocks define M. The score is lexical similarity, not semantic embedding similarity, recognition accuracy, or confidence probability.
- **คำอธิบายภาษาไทย**: คะแนน 0.75 เป็นเกณฑ์ของโครงการ ต้องประเมินคำถามไทยและอังกฤษจริง ไม่ควรเรียกว่าโอกาสถูกต้อง 75 เปอร์เซ็นต์
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `apps/voice/service.py` (Line 125): *def match_faq(*
- **Supporting References**:
  * `[38]` Python Software Foundation (n.d.) — *difflib — Helpers for computing deltas* ([Link](https://docs.python.org/3/library/difflib.html))
  * `[114]` CUIR / Chulalongkorn University (2023) — *Thai language sentiment analysis with a hybrid method on WangchanBERTa-CNN-BiLSTM* ([Link](https://doi.org/10.58837/chula.the.2023.1363))
  * `[124]` C. Wutiwiwatchai, A. Thangthai, A. Chotimongkol, C. Hansakunbuntheung, and N. Thatphithakkul (2011) — *Accent level adjustment in bilingual Thai-English text-to-speech synthesis* ([Link](https://doi.org/10.1109/asru.2011.6163947))
  * `[135]` K. Grerkiat and V. Rattawut (2023) — *Applying Self-Assessment Manikin (SAM) to Evaluate the Emotional Responses to the Service Robot Feature* ([Link](https://doi.org/10.1109/icbir57571.2023.10147577))
  * `[141]` T. Fong, I. Nourbakhsh, and K. Dautenhahn (2003) — *A survey of socially interactive robots* ([Link](https://doi.org/10.1016/s0921-8890(02)00372-x))

---

### Card: Whisper transcription backend (การถอดเสียงด้วย Whisper)
- **ID**: `speech-recognition` | **Group**: *Voice and conversation* | **Status**: `IMPLEMENTED`

```text
audio → preprocessing → WhisperModel.transcribe → text
```

- **English Description**: The service imports faster_whisper and loads a configurable model. Whisper is the research basis; faster-whisper is the inference implementation. Deployment must record language, model size, compute type and package versions.
- **คำอธิบายภาษาไทย**: โค้ดที่ import โมเดลไม่ได้ยืนยันว่าโหลดสำเร็จ ต้องแยกเอกสารอัลกอริทึมออกจากผลทดสอบบนเครื่องจริง
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `apps/voice/service.py` (Line 172): *from faster_whisper import WhisperModel*
- **Supporting References**:
  * `[32]` A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey and I. Sutskever (2022) — *Robust Speech Recognition via Large-Scale Weak Supervision* ([Link](https://arxiv.org/abs/2212.04356))
  * `[33]` SYSTRAN and contributors (n.d.) — *faster-whisper: Faster Whisper transcription with CTranslate2* ([Link](https://github.com/SYSTRAN/faster-whisper))
  * `[106]` P. Kantithammakorn, P. Punyabukkana, and P. N. Pratanwanich (2022) — *Using Automatic Speech Recognition to Assess Thai Speech Language Fluency in the Montreal Cognitive Assessment (MoCA)* ([Link](https://doi.org/10.3390/s22041583))
  * `[111]` N. Theera-Umpon, S. Chansareewittaya, and S. Auephanwiriyakul (2011) — *Phoneme and tonal accent recognition for Thai speech* ([Link](https://doi.org/10.1016/j.eswa.2011.04.142))
  * `[118]` C. Wutiwiwatchai, V. Chunwijitra, S. Chunwijitra, P. Sertsi, S. Kasuriya, P. Chootrakool, and K. Thangthai (2018) — *The NECTEC 2015 Thai Open-Domain Automatic Speech Recognition System* ([Link](https://doi.org/10.1007/978-3-319-70016-8_11))
  * `[120]` W. Phatthiyaphaibun, C. Chaksangchaichot, T. Rakthammanon, E. Chuangsuwanich, and S. Nutanong (2023) — *Crowdsourced Data Validation for ASR Training* ([Link](https://doi.org/10.21437/interspeech.2023-389))
  * `[128]` J. Klangkankullapun, P. Seresangtakul, and P. Janyoi (2025) — *Thai Elderly Speech Recognition Using Transfer Learning* ([Link](https://doi.org/10.1109/icsec67360.2025.11298001))
  * `[139]` L. R. Rabiner and R. W. Schafer (2010) — *Theory and Applications of Digital Speech Processing* ([Link](https://www.pearson.com/en-us/subject-catalog/p/theory-and-applications-of-digital-speech-processing/P200000003507))

---

### Card: Local response generation and NF4 quantization (โมเดลตอบคำถามในเครื่องและการลดบิต NF4)
- **ID**: `local-llm` | **Group**: *Voice and conversation* | **Status**: `IMPLEMENTED`

```text
P(next token | previous tokens); quantized weights + configured generation limits
```

- **English Description**: Voice loads a configured checkpoint through Transformers and PyTorch, with NF4 and double quantization settings. This establishes an implementation path, not successful loading or real-time performance.
- **คำอธิบายภาษาไทย**: QLoRA ใช้อธิบายแนวคิด NF4 ได้ แต่โครงการนี้แสดง inference ไม่ใช่การฝึก fine-tune ต้องบันทึกรุ่น checkpoint และฮาร์ดแวร์
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `apps/voice/service.py` (Line 314): *def _load_llm(*
- **Supporting References**:
  * `[36]` Qwen Team (2026) — *Qwen3.5-4B model card* ([Link](https://huggingface.co/Qwen/Qwen3.5-4B))
  * `[34]` T. Wolf et al. (2020) — *Transformers: State-of-the-Art Natural Language Processing* ([Link](https://aclanthology.org/2020.emnlp-demos.6/))
  * `[35]` A. Paszke et al. (2019) — *PyTorch: An Imperative Style, High-Performance Deep Learning Library* ([Link](https://arxiv.org/abs/1912.01703))
  * `[37]` T. Dettmers, A. Pagnoni, A. Holtzman and L. Zettlemoyer (2023) — *QLoRA: Efficient Finetuning of Quantized LLMs* ([Link](https://arxiv.org/abs/2305.14314))
  * `[114]` CUIR / Chulalongkorn University (2023) — *Thai language sentiment analysis with a hybrid method on WangchanBERTa-CNN-BiLSTM* ([Link](https://doi.org/10.58837/chula.the.2023.1363))

---

### Card: Browser microphone and recording lifecycle (วงจรการเปิดไมโครโฟนและบันทึกเสียง)
- **ID**: `microphone-browser` | **Group**: *Voice and conversation* | **Status**: `IMPLEMENTED`

```text
getUserMedia → MediaRecorder → audio blob → transcription request
```

- **English Description**: The current page obtains a media stream and records audio. Capture permission, recording completion and stopping tracks are distinct from model inference and speech playback.
- **คำอธิบายภาษาไทย**: การมี MediaRecorder ไม่ได้พิสูจน์ว่าเป็นบทสนทนา streaming ต้องทดสอบสิทธิ์ไมโครโฟน รูปแบบเสียง และการหยุดทรัพยากร
- **Units & Variables**: Defined beside each symbol in the equation.
- **Engineering Caveat / ข้อควรระวัง**: The reviewed main-tree talk() records until the user stops, then uploads a Blob. A task marked done elsewhere does not prove continuous/full-duplex conversation in this exact file.
- **Implementation Code Location**:
  * `apps/voice/index.html` (Line 224): *getUserMedia*
- **Supporting References**:
  * `[47]` W3C (n.d.) — *Media Capture and Streams* ([Link](https://www.w3.org/TR/mediacapture-streams/))
  * `[48]` W3C (n.d.) — *MediaStream Recording* ([Link](https://www.w3.org/TR/mediastream-recording/))

---

### Card: Conversation latency and turn-taking (ความหน่วงและการผลัดกันพูด)
- **ID**: `conversation-latency` | **Group**: *Voice and conversation* | **Status**: `EVALUATION`

```text
L_total = L_endpoint + L_upload + L_STT + L_answer + L_TTS + L_playback_start
real-time factor RTF = processing_time / audio_duration
```

- **English Description**: This is a proposed measurement decomposition. Measure each segment on a shared clock where possible and report cold versus warm runs. Continuous listen/respond cycles do not imply simultaneous full-duplex conversation.
- **คำอธิบายภาษาไทย**: ต้องแยกเวลารอตรวจจบคำพูด การถอดเสียง การสร้างคำตอบ และเริ่มเล่นเสียง พร้อมป้องกันไมโครโฟนรับเสียงตอบของตนเอง
- **Units & Variables**: Defined beside each symbol in the equation.
- **Engineering Caveat / ข้อควรระวัง**: Stage sum assumes sequential non-overlapping stages; for concurrent pipelines measure the actual critical path. Main-tree talk() remains manual recording in this snapshot; no full-duplex or latency benchmark is claimed.
- **Implementation Code Location**:
  * `apps/voice/service.py` (Line 179): *def listen(*
  * `apps/voice/service.py` (Line 250): *def say(*
- **Supporting References**:
  * `[53]` Python Software Foundation (n.d.) — *time — Time access and conversions* ([Link](https://docs.python.org/3/library/time.html))
  * `[66]` W3C (n.d.) — *High Resolution Time* ([Link](https://www.w3.org/TR/hr-time-3/))
  * `[33]` SYSTRAN and contributors (n.d.) — *faster-whisper: Faster Whisper transcription with CTranslate2* ([Link](https://github.com/SYSTRAN/faster-whisper))
  * `[67]` W3C (n.d.) — *Web Audio API 1.1* ([Link](https://www.w3.org/TR/webaudio/))
  * `[98]` D. Macháček, R. Dabre and O. Bojar (2023) — *Turning Whisper into Real-Time Transcription System* ([Link](https://aclanthology.org/2023.ijcnlp-demo.3/))

---

### Card: Word/character error rate (อัตราผิดพลาดระดับคำและอักขระ)
- **ID**: `speech-evaluation` | **Group**: *Voice and conversation* | **Status**: `EVALUATION`

```text
WER = (substitutions + deletions + insertions) / reference_words
CER = character_edit_distance / reference_characters
```

- **English Description**: Use a fixed reference transcript and scoring policy. Thai requires an explicit segmentation policy; reporting CER alongside WER reduces ambiguity from word boundaries.
- **คำอธิบายภาษาไทย**: ต้องกำหนดการตัดคำ การเว้นวรรค ตัวเลข และเครื่องหมายก่อนประเมิน ใช้ชุดเสียงทดสอบที่ไม่ปนกับชุดปรับแต่ง
- **Units & Variables**: Defined beside each symbol in the equation.
- **Engineering Caveat / ข้อควรระวัง**: WER can exceed 100%. Define Thai word segmentation, Unicode normalization, punctuation, CER code-point/grapheme policy and empty-reference handling before comparing systems.
- **Implementation Code Location**:
  * `apps/voice/bench/run_bench.py` (Line 24): *import*
- **Supporting References**:
  * `[39]` National Institute of Standards and Technology (n.d.) — *Speech Recognition Scoring Toolkit (SCTK)* ([Link](https://github.com/usnistgov/SCTK))
  * `[32]` A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey and I. Sutskever (2022) — *Robust Speech Recognition via Large-Scale Weak Supervision* ([Link](https://arxiv.org/abs/2212.04356))
  * `[107]` P. Prakrankamanant (2021) — *Data augmentation for Thai natural language processing using different tokenization* ([Link](https://doi.org/10.58837/chula.the.2021.98))
  * `[118]` C. Wutiwiwatchai, V. Chunwijitra, S. Chunwijitra, P. Sertsi, S. Kasuriya, P. Chootrakool, and K. Thangthai (2018) — *The NECTEC 2015 Thai Open-Domain Automatic Speech Recognition System* ([Link](https://doi.org/10.1007/978-3-319-70016-8_11))
  * `[120]` W. Phatthiyaphaibun, C. Chaksangchaichot, T. Rakthammanon, E. Chuangsuwanich, and S. Nutanong (2023) — *Crowdsourced Data Validation for ASR Training* ([Link](https://doi.org/10.21437/interspeech.2023-389))
  * `[128]` J. Klangkankullapun, P. Seresangtakul, and P. Janyoi (2025) — *Thai Elderly Speech Recognition Using Transfer Learning* ([Link](https://doi.org/10.1109/icsec67360.2025.11298001))
  * `[139]` L. R. Rabiner and R. W. Schafer (2010) — *Theory and Applications of Digital Speech Processing* ([Link](https://www.pearson.com/en-us/subject-catalog/p/theory-and-applications-of-digital-speech-processing/P200000003507))

---

### Card: Face embeddings and comparison metrics (เวกเตอร์ใบหน้าและการวัดความใกล้เคียง)
- **ID**: `face-embeddings` | **Group**: *Face integration* | **Status**: `RELATED`

```text
cosine(x,y) = x·y/(||x||₂ ||y||₂)
for unit vectors: ||x-y||₂² = 2 - 2 cosine(x,y)
```

- **English Description**: FaceNet and ArcFace provide related embedding literature. The visible Mice adapter consumes an external recognition result; it does not establish which embedding model or metric that service runs.
- **คำอธิบายภาษาไทย**: ต้องตรวจ repository และรุ่นโมเดลของบริการจดจำใบหน้าแยกต่างหากก่อนอ้างว่าใช้ FaceNet หรือ ArcFace จริง
- **Units & Variables**: Defined beside each symbol in the equation.
- **Engineering Caveat / ข้อควรระวัง**: Do not compare thresholds across different models, normalization rules or distance definitions.
- **Implementation Code Location**:
  * `apps/faces/service.py` (Line 32): *import*
- **Supporting References**:
  * `[40]` F. Schroff, D. Kalenichenko and J. Philbin (2015) — *FaceNet: A Unified Embedding for Face Recognition and Clustering* ([Link](https://arxiv.org/abs/1503.03832))
  * `[41]` J. Deng, J. Guo, N. Xue and S. Zafeiriou (2019) — *ArcFace: Additive Angular Margin Loss for Deep Face Recognition* ([Link](https://arxiv.org/abs/1801.07698))
  * `[45]` InsightFace contributors (n.d.) — *InsightFace: 2D and 3D Face Analysis* ([Link](https://github.com/deepinsight/insightface))
  * `[109]` S. Malakar, W. Chiracharit, K. Chamnongthai, and T. Charoenpong (2021) — *Masked Face Recognition Using Principal component analysis and Deep learning* ([Link](https://doi.org/10.1109/ecti-con51831.2021.9454857))
  * `[129]` R. Khoeun, W. Yookwan, P. Chophuk, A. Rodtook, and K. Chinnasarn (2023) — *Emotion Recognition of Partial Face Using Star-Like Particle Polygon Estimation* ([Link](https://doi.org/10.1109/access.2023.3305514))

---

### Card: Triplet and angular-margin training objectives (ฟังก์ชันสูญเสีย triplet และ angular margin)
- **ID**: `face-loss` | **Group**: *Face integration* | **Status**: `RELATED`

```text
triplet loss = max(0, ||a-p||₂² - ||a-n||₂² + margin)
ArcFace target logit = scale × cos(theta_target + angular_margin)
```

- **English Description**: These are training concepts for the literature review. They are not losses computed by the Mice adapter and do not demonstrate that this project trained a recognition network.
- **คำอธิบายภาษาไทย**: ใช้เปรียบเทียบแนวคิดงานวิจัย ไม่ใช่อ้างว่าโครงการฝึกเครือข่ายหรือใช้ loss นี้ในโค้ดของ Mice
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `apps/faces/service.py` (Line 32): *import*
- **Supporting References**:
  * `[40]` F. Schroff, D. Kalenichenko and J. Philbin (2015) — *FaceNet: A Unified Embedding for Face Recognition and Clustering* ([Link](https://arxiv.org/abs/1503.03832))
  * `[41]` J. Deng, J. Guo, N. Xue and S. Zafeiriou (2019) — *ArcFace: Additive Angular Margin Loss for Deep Face Recognition* ([Link](https://arxiv.org/abs/1801.07698))

---

### Card: Detection, landmarks and identity are separate stages (แยกการตรวจใบหน้า จุดสังเกต และการระบุตัวบุคคล)
- **ID**: `face-detection` | **Group**: *Face integration* | **Status**: `RELATED`

```text
image → face detection → alignment → embedding → identity decision
```

- **English Description**: RetinaFace supports discussion of detection and landmarks. Mice’s event consumer cannot verify the detector, alignment, training data or liveness mechanisms used upstream.
- **คำอธิบายภาษาไทย**: ระบบแจ้งว่าพบบุคคลไม่ได้ยืนยันว่ามี liveness หรือป้องกันภาพปลอม ต้องอ้างและทดสอบบริการต้นทางจริง
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `apps/faces/service.py` (Line 32): *import*
- **Supporting References**:
  * `[42]` J. Deng, J. Guo, Y. Zhou, J. Yu, I. Kotsia and S. Zafeiriou (2019) — *RetinaFace: Single-stage Dense Face Localisation in the Wild* ([Link](https://arxiv.org/abs/1905.00641))
  * `[45]` InsightFace contributors (n.d.) — *InsightFace: 2D and 3D Face Analysis* ([Link](https://github.com/deepinsight/insightface))
  * `[112]` S. Auephanwiriyakul, S. Phitakwinai, and W. Suttapak (2013) — *Thai sign language translation using Scale Invariant Feature Transform and Hidden Markov Models* ([Link](https://doi.org/10.1016/j.patrec.2013.04.017))
  * `[129]` R. Khoeun, W. Yookwan, P. Chophuk, A. Rodtook, and K. Chinnasarn (2023) — *Emotion Recognition of Partial Face Using Star-Like Particle Polygon Estimation* ([Link](https://doi.org/10.1109/access.2023.3305514))
  * `[130]` U. Suttapakti and A. Bunpeng (2021) — *Adaptive Kernel Transform for Face Recognition Under Uneven Illumination Conditions* ([Link](https://doi.org/10.1109/icsec53205.2021.9684605))
  * `[136]` N. Otanasap and P. Boonbrahm (2017) — *Pre-impact fall detection system using dynamic threshold and 3D bounding box* ([Link](https://doi.org/10.1117/12.2266822))
  * `[142]` D. G. Lowe (2004) — *Distinctive Image Features from Scale-Invariant Keypoints* ([Link](https://doi.org/10.1023/b:visi.0000029664.99615.94))

---

### Card: Recognition errors and event-level evaluation (การประเมินความผิดพลาดของการรู้จำและเหตุการณ์)
- **ID**: `face-evaluation` | **Group**: *Face integration* | **Status**: `EVALUATION`

```text
precision = TP/(TP+FP); recall = TP/(TP+FN)
F1 = 2TP/(2TP+FP+FN)
FMR = false matches / impostor comparisons
FNMR = false non-matches / genuine comparisons
```

- **English Description**: Define sample unit (frame, comparison, person or event), unknown identities and denominator. FMR/FNMR at a threshold is different from retrieval precision/recall; report the task being measured.
- **คำอธิบายภาษาไทย**: อย่าปนความถูกต้องต่อเฟรมกับความถูกต้องต่อเหตุการณ์ และอย่าใช้บุคคลเดียวกันรั่วระหว่างชุดปรับเกณฑ์กับชุดทดสอบ
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `apps/faces/service.py` (Line 32): *import*
  * `qc/checks/check_faces_dedupe.py` (Line 25): *import*
- **Supporting References**:
  * `[40]` F. Schroff, D. Kalenichenko and J. Philbin (2015) — *FaceNet: A Unified Embedding for Face Recognition and Clustering* ([Link](https://arxiv.org/abs/1503.03832))
  * `[41]` J. Deng, J. Guo, N. Xue and S. Zafeiriou (2019) — *ArcFace: Additive Angular Margin Loss for Deep Face Recognition* ([Link](https://arxiv.org/abs/1801.07698))
  * `[64]` NIST/SEMATECH (n.d.) — *e-Handbook of Statistical Methods: Confidence Intervals for a Binomial Proportion* ([Link](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm))
  * `[100]` ISO/IEC (2021) — *ISO/IEC 19795-1:2021 — Information technology — Biometric performance testing and reporting — Part 1: Principles and framework* ([Link](https://www.iso.org/standard/73515.html))
  * `[99]` P. Grother, M. Ngan and K. Hanaoka (2019) — *Face Recognition Vendor Test Part 3: Demographic Effects* ([Link](https://www.nist.gov/publications/face-recognition-vendor-test-part-3-demographic-effects))

---

### Card: Transport latency, success and percentiles (สถิติความหน่วงและอัตราสำเร็จของการสื่อสาร)
- **ID**: `latency-statistics` | **Group**: *Experiments and thesis evidence* | **Status**: `IMPLEMENTED`

```text
RTT_i = receive_time_i - send_time_i
success = replies / requests; loss = 1 - success
mean = Σx_i/n; s = sqrt(Σ(x_i-mean)²/(n-1))
Quantile p: k=(n-1)p; Q(p)=x_floor(k)+(k-floor(k))(x_ceil(k)-x_floor(k))
```

- **English Description**: The transport bench measures round trips and reports mean/p95/extrema. Its percentile() implementation is the definition used by that report. Separate failed/time-out requests from successful latency samples and disclose both counts.
- **คำอธิบายภาษาไทย**: รายงานจำนวนส่ง จำนวนสำเร็จ timeout และสูตร percentile ที่ใช้ เวลา RTT ไม่ใช่เวลาเดินทางขาเดียวหรือความหน่วงมอเตอร์จริง
- **Units & Variables**: Defined beside each symbol in the equation.
- **Engineering Caveat / ข้อควรระวัง**: Quantiles use sorted successful samples with linear interpolation, not nearest-rank. Sample SD requires n≥2; a timeout rate is not necessarily physical packet loss.
- **Implementation Code Location**:
  * `scient_test/tools/bench.py` (Line 51): *def percentile(*
- **Supporting References**:
  * `[53]` Python Software Foundation (n.d.) — *time — Time access and conversions* ([Link](https://docs.python.org/3/library/time.html))
  * `[65]` Python Software Foundation (n.d.) — *statistics — Mathematical statistics functions* ([Link](https://docs.python.org/3/library/statistics.html))

---

### Card: Confidence intervals for mean and success rate (ช่วงความเชื่อมั่นของค่าเฉลี่ยและอัตราสำเร็จ)
- **ID**: `confidence-intervals` | **Group**: *Experiments and thesis evidence* | **Status**: `EVALUATION`

```text
mean CI = mean ± t_(1-α/2,n-1) × s/√n
Wilson center = (p_hat + z²/(2n))/(1+z²/n)
Wilson halfwidth = z sqrt(p_hat(1-p_hat)/n+z²/(4n²))/(1+z²/n)
```

- **English Description**: Suggested thesis analysis beyond the current descriptive bench report. State independence and distribution assumptions; serially correlated latency requires additional treatment.
- **คำอธิบายภาษาไทย**: ช่วงความเชื่อมั่นค่าเฉลี่ยไม่ใช่ช่วงที่ครอบคลุมข้อมูลทุกครั้ง และผลสำเร็จ 100 เปอร์เซ็นต์ในตัวอย่างไม่รับประกันความเชื่อถือได้สมบูรณ์
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `scient_test/tools/bench.py` (Line 36): *import statistics*
- **Supporting References**:
  * `[63]` NIST/SEMATECH (n.d.) — *e-Handbook of Statistical Methods: Confidence Limits for the Mean* ([Link](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm))
  * `[64]` NIST/SEMATECH (n.d.) — *e-Handbook of Statistical Methods: Confidence Intervals for a Binomial Proportion* ([Link](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm))

---

### Card: Calibration uncertainty propagation (การรวมความไม่แน่นอนของการวัด)
- **ID**: `measurement-uncertainty` | **Group**: *Experiments and thesis evidence* | **Status**: `EVALUATION`

```text
u_c²(y) = Σ_i (∂f/∂x_i)² u²(x_i) + 2Σ_(i&lt;j)(∂f/∂x_i)(∂f/∂x_j) cov(x_i,x_j)
U = k u_c
```

- **English Description**: Use the measurement model to propagate encoder scale, gear dimensions, joint-angle and timing uncertainty. Distinguish uncertainty from observed error and state the coverage factor.
- **คำอธิบายภาษาไทย**: ต้องระบุเครื่องมือ ความละเอียด วิธีสอบเทียบ ความแปรปรวน และสหสัมพันธ์ ห้ามใส่ค่าความไม่แน่นอนที่ไม่ได้วัดหรือประเมิน
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `scient_test/tests/T1_nong_module.md` (Line 1): *#*
- **Supporting References**:
  * `[62]` JCGM (2008) — *Evaluation of measurement data — Guide to the expression of uncertainty in measurement* ([Link](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf))
  * `[125]` K. Nontapot and C. Nutsathaporn (2023) — *Uncertainty reduction of CO2 laser calibration system in National Institute of Metrology (Thailand)* ([Link](https://doi.org/10.1117/12.2671699))

---

### Card: Position error and repeated-pose dispersion (ความคลาดเคลื่อนตำแหน่งและการกระจายเมื่อทำซ้ำ)
- **ID**: `robot-repeatability` | **Group**: *Experiments and thesis evidence* | **Status**: `EVALUATION`

```text
e_i = measured_position_i - reference_position
RMSE = sqrt(Σ_i ||e_i||₂²/n)
```

- **English Description**: These are general error statistics for a proposed robot experiment, not a reproduction of every ISO 9283 criterion. Use the standard’s full procedure before claiming its named metrics or conformance.
- **คำอธิบายภาษาไทย**: กำหนดพิกัดอ้างอิง โหลด ความเร็ว จำนวนรอบ และเครื่องมือวัดแยกจากค่าที่แสดงบน UI สูตรนี้ไม่ใช่การรับรองตาม ISO
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `scient_test/tests/T1_nong_module.md` (Line 1): *#*
  * `scient_test/tests/T2_lift_module.md` (Line 1): *#*
- **Supporting References**:
  * `[58]` ISO (1998) — *ISO 9283:1998 — Manipulating industrial robots — Performance criteria and related test methods* ([Link](https://www.iso.org/standard/22244.html))
  * `[62]` JCGM (2008) — *Evaluation of measurement data — Guide to the expression of uncertainty in measurement* ([Link](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf))
  * `[65]` Python Software Foundation (n.d.) — *statistics — Mathematical statistics functions* ([Link](https://docs.python.org/3/library/statistics.html))

---

### Card: Native tests, fake modules and physical experiments (แยกการทดสอบซอฟต์แวร์กับฮาร์ดแวร์จริง)
- **ID**: `software-verification` | **Group**: *Experiments and thesis evidence* | **Status**: `IMPLEMENTED`

```text
regression evidence: fail without fix → pass with fix
software test result ≠ physical performance measurement
```

- **English Description**: Native mathematical tests and fake-module wire assertions demonstrate specified software behavior. They cannot establish servo torque, bus noise tolerance, physical accuracy or acoustic quality.
- **คำอธิบายภาษาไทย**: วิทยานิพนธ์ควรแยกตารางผล native test, integration test และการทดลองบนอุปกรณ์จริงอย่างชัดเจน
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `qc/README.md` (Line 1): *#*
  * `firmware/src/modules/nong/NongMath.h` (Line 35): *inline float*
- **Supporting References**:
  * `[52]` PlatformIO (n.d.) — *Unit Testing* ([Link](https://docs.platformio.org/en/latest/advanced/unit-testing/index.html))
  * `[58]` ISO (1998) — *ISO 9283:1998 — Manipulating industrial robots — Performance criteria and related test methods* ([Link](https://www.iso.org/standard/22244.html))
  * `[62]` JCGM (2008) — *Evaluation of measurement data — Guide to the expression of uncertainty in measurement* ([Link](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf))

---

### Card: Operator usability and accessibility (ความใช้งานง่ายและการเข้าถึงของผู้ควบคุม)
- **ID**: `operator-accessibility` | **Group**: *Studio and operator interface* | **Status**: `EVALUATION`

```text
contrast ratio = (L_lighter + 0.05)/(L_darker + 0.05)
```

- **English Description**: WCAG defines relative luminance and criterion-specific requirements; use its full definitions when computing contrast. Human-centred design and HRI literature support task-based evaluation of controls and feedback.
- **คำอธิบายภาษาไทย**: ตรวจแป้นพิมพ์ focus ป้ายชื่อ สถานะ และการใช้งานจริงบนจอหลายขนาด ไม่สรุปว่าใช้งานง่ายจากความสวยงามเพียงอย่างเดียว
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `shared/web/mice.css` (Line 38): *:root*
  * `qc/checks/check_responsive.py` (Line 11): *import*
- **Supporting References**:
  * `[46]` W3C (2023) — *Web Content Accessibility Guidelines (WCAG) 2.2* ([Link](https://www.w3.org/TR/WCAG22/))
  * `[61]` ISO (2019) — *ISO 9241-210:2019 — Ergonomics of human-system interaction — Part 210: Human-centred design for interactive systems* ([Link](https://www.iso.org/standard/77520.html))
  * `[57]` M. A. Goodrich and A. C. Schultz (2007) — *Human–Robot Interaction: A Survey* ([Link](https://doi.org/10.1561/1100000005))

---

### Card: Risk assessment and stopping functions (ประเมินความเสี่ยงและหน้าที่หยุดการทำงาน)
- **ID**: `motion-safety` | **Group**: *Safety and scope* | **Status**: `EVALUATION`

```text
hazard → foreseeable situation → risk assessment → risk reduction → verification
```

- **English Description**: Use ISO 12100 for the risk-assessment framework and ISO 13850 as related emergency-stop design literature. A network STOP message, software clamp or browser control does not establish a safety-rated stop.
- **คำอธิบายภาษาไทย**: ต้องวิเคราะห์การหนีบ โหลดตก ไฟฟ้า การเริ่มเอง และการขาดสัญญาณ การอ้างมาตรฐานไม่ได้เท่ากับผ่านการรับรอง
- **Units & Variables**: Defined beside each symbol in the equation.
- **Implementation Code Location**:
  * `firmware/src/modules/lift/LiftModule.cpp` (Line 1): *include*
  * `firmware/src/core/BrownoutGuard.cpp` (Line 1): *include*
- **Supporting References**:
  * `[59]` ISO (2010) — *ISO 12100:2010 — Safety of machinery — General principles for design — Risk assessment and risk reduction* ([Link](https://www.iso.org/standard/51528.html))
  * `[60]` ISO (2015) — *ISO 13850:2015 — Safety of machinery — Emergency stop function — Principles for design* ([Link](https://www.iso.org/standard/59970.html))
  * `[121]` R. Phuengsuk and J. Suthakorn (2016) — *A study on risk assessment for improving reliability of rescue robots* ([Link](https://doi.org/10.1109/robio.2016.7866399))
  * `[131]` P. Neranon and R. Bicker (2016) — *Force/position control of a robot manipulator for human-robot interaction* ([Link](https://doi.org/10.2298/tsci151005036n))
  * `[135]` K. Grerkiat and V. Rattawut (2023) — *Applying Self-Assessment Manikin (SAM) to Evaluate the Emotional Responses to the Service Robot Feature* ([Link](https://doi.org/10.1109/icbir57571.2023.10147577))
  * `[141]` T. Fong, I. Nourbakhsh, and K. Dautenhahn (2003) — *A survey of socially interactive robots* ([Link](https://doi.org/10.1016/s0921-8890(02)00372-x))

---

### Card: Studio configurable forward kinematics (คิเนเมติกส์ตรงของ Studio ที่ปรับตั้งได้)
- **ID**: `studio-fk` | **Group**: *Nong — the humanoid* | **Status**: `IMPLEMENTED`

```text
Q_joint = Q_mount_tilt × Q_axis(q-zero)
T_world = T_parent T_local; p_world = T_world p_local
```

- **English Description**: Studio composes Three.js groups with per-joint axes, signs, zero offsets, mounting tilts and configured lengths. fkPoints() neutralizes waist/shrug for its body-relative arm readout and collision calculations.
- **คำอธิบายภาษาไทย**: Studio ประกอบการแปลงพิกัดตามแกน ทิศหมุน จุดศูนย์ มุมติดตั้ง และความยาวที่ตั้งไว้ ส่วน fkPoints ตั้งเอวและไหล่เป็นค่ากลางเพื่อคำนวณแขนเทียบลำตัว
- **Units & Variables**: Positions: mm; user angles: degrees, converted to radians
- **Engineering Caveat / ข้อควรระวัง**: Changing the preview dimensions does not calibrate physical link lengths automatically.
- **Implementation Code Location**:
  * `nong/main_python_set_nong/web/app.js` (Line 825): *applyPose()*
  * `nong/main_python_set_nong/web/app.js` (Line 1262): *fkPoints()*
- **Supporting References**:
  * `[1]` K. M. Lynch and F. C. Park (2017) — *Modern Robotics: Mechanics, Planning, and Control* ([Link](https://modernrobotics.northwestern.edu/nu-gm-book-resource/))
  * `[54]` Three.js contributors (n.d.) — *Three.js documentation* ([Link](https://threejs.org/docs/))
  * `[68]` John J. Craig (2017) — *Introduction to Robotics: Mechanics and Control* ([Link](https://www.pearson.com/en-us/subject-catalog/p/introduction-to-robotics-mechanics-and-control/P200000003304/9780133489798))

---

### Card: PCM sampling, bandwidth and I2S clocking (การสุ่มตัวอย่างเสียง PCM และนาฬิกา I2S)
- **ID**: `audio-pcm` | **Group**: *Audio and voice* | **Status**: `DERIVED`

```text
PCM bitrate = f_s × channels × bits_per_sample
22050 × 1 × 16 = 352800 bit/s; 2-byte sample interval = 1/22050 s
I2S BCLK = f_s × slots_per_frame × bits_per_slot
For an ideally band-limited input, f_s &gt; 2 f_max
```

- **English Description**: Raw network payload and the digital I2S wire format have different rates. The speaker stream is 16-bit mono; output duplicates mono samples for the output channels. I2S slot width may exceed sample width.
- **คำอธิบายภาษาไทย**: อัตราข้อมูลเสียงผ่านเครือข่ายต่างจากอัตรานาฬิกา I2S โค้ดส่ง PCM โมโน 16 บิตและทำสำเนาตัวอย่างให้ช่องเอาต์พุต ต้องใช้ขนาดสล็อตจริงในการคำนวณ BCLK และมีตัวกรองป้องกัน aliasing
- **Units & Variables**: f_s,BCLK: Hz; bitrate: bit/s
- **Engineering Caveat / ข้อควรระวัง**: 352800 bit/s excludes UDP/IP/Wi-Fi overhead and does not prove sustained throughput.
- **Implementation Code Location**:
  * `firmware/src/core/AudioStream.h` (Line 25): *Default PCM format*
  * `firmware/src/core/AudioStream.cpp` (Line 35): *Output sampling configuration*
- **Supporting References**:
  * `[96]` S. W. Smith (n.d.) — *The Scientist and Engineer’s Guide to Digital Signal Processing: The Sampling Theorem* ([Link](https://www.dspguide.com/ch3/2.htm))
  * `[27]` NXP Semiconductors (2022) — *I2S bus specification* ([Link](https://www.nxp.com/docs/en/user-manual/UM11732.pdf))
  * `[28]` Maxim Integrated / Analog Devices (n.d.) — *MAX98357A/MAX98357B: Tiny, Low-Cost, PCM Class D Amplifier with Class AB Performance* ([Link](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf))
  * `[30]` E. F. Philhower III and contributors (n.d.) — *ESP8266Audio* ([Link](https://github.com/earlephilhower/ESP8266Audio))

---

### Card: UDP audio buffer and startup latency (บัฟเฟอร์เสียง UDP และเวลารอเริ่มเล่น)
- **ID**: `audio-buffer` | **Group**: *Audio and voice* | **Status**: `IMPLEMENTED`

```text
capacity = floor(f_s × buffer_ms/1000) samples
memory = 2 × capacity bytes for int16 mono
22050 Hz × 0.2 s = 4410 samples = 8820 bytes
priming threshold = floor(capacity/2), about 100 ms of audio
```

- **English Description**: AudioStream reserves a 200 ms ring and primes to half capacity before feeding samples. One ring slot remains unused to distinguish full and empty; underflow triggers re-priming. Packet loss, reordering and network jitter require separate measurement.
- **คำอธิบายภาษาไทย**: AudioStream จองบัฟเฟอร์ 200 มิลลิวินาทีและรอข้อมูลครึ่งบัฟเฟอร์ก่อนเล่น เว้นหนึ่งช่องเพื่อแยกสถานะเต็มและว่าง เมื่อข้อมูลหมดจะรอเติมใหม่ ต้องวัดการสูญหายและความแปรปรวนของเครือข่ายเพิ่มเติม
- **Units & Variables**: Time: ms; sample count: integer; memory: bytes
- **Engineering Caveat / ข้อควรระวัง**: Priming duration is not the complete microphone-to-speaker latency. UDP has no delivery or ordering guarantee.
- **Implementation Code Location**:
  * `firmware/src/core/AudioStream.cpp` (Line 22): *AudioStream ring allocation*
  * `firmware/src/core/AudioStream.cpp` (Line 86): *AudioStream::feed()*
- **Supporting References**:
  * `[95]` L. Eggert, G. Fairhurst and G. Shepherd (2017) — *UDP Usage Guidelines* ([Link](https://www.rfc-editor.org/rfc/rfc8085.html))
  * `[30]` E. F. Philhower III and contributors (n.d.) — *ESP8266Audio* ([Link](https://github.com/earlephilhower/ESP8266Audio))

---

### Card: Windows speech synthesis and WAV caching (การสังเคราะห์เสียง Windows และแคช WAV)
- **ID**: `windows-tts` | **Group**: *Audio and voice* | **Status**: `IMPLEMENTED`

```text
text + selected installed voice → WinRT SpeechSynthesizer → WAV
cache key = MD5(voice_identity + newline + text)
```

- **English Description**: The service invokes tts.ps1, which uses Windows.Media.SpeechSynthesis. A per-service lock serializes synthesis and an atomic replacement publishes the cache file. Cached and uncached TTS latency should be measured separately.
- **คำอธิบายภาษาไทย**: บริการเรียก tts.ps1 เพื่อใช้ Windows.Media.SpeechSynthesis มีล็อกป้องกันการสังเคราะห์ซ้อนและบันทึกแคชแบบอะตอมิก ต้องแยกผลเวลาตอบสนองระหว่างกรณีมีแคชและไม่มีแคช
- **Units & Variables**: Output: WAV bytes; latency: ms
- **Engineering Caveat / ข้อควรระวัง**: MD5 here names cached audio; it is not authentication. Installed Thai voices must be checked on the actual demonstration PC.
- **Implementation Code Location**:
  * `apps/voice/tts.ps1` (Line 20): *WinRT voice backend*
  * `apps/voice/service.py` (Line 250): *Voice synthesis/cache method*
- **Supporting References**:
  * `[97]` Microsoft (n.d.) — *SpeechSynthesizer Class (Windows.Media.SpeechSynthesis)* ([Link](https://learn.microsoft.com/en-ca/uwp/api/windows.media.speechsynthesis.speechsynthesizer?view=winrt-28000))
  * `[25]` S. Turner and L. Chen (2011) — *Updated Security Considerations for the MD5 Message-Digest and the HMAC-MD5 Algorithms* ([Link](https://www.rfc-editor.org/rfc/rfc6151.html))
  * `[124]` C. Wutiwiwatchai, A. Thangthai, A. Chotimongkol, C. Hansakunbuntheung, and N. Thatphithakkul (2011) — *Accent level adjustment in bilingual Thai-English text-to-speech synthesis* ([Link](https://doi.org/10.1109/asru.2011.6163947))

---

### Card: Streaming recognition as related future work (งานที่เกี่ยวข้องกับการรู้จำเสียงแบบสตรีม)
- **ID**: `streaming-stt` | **Group**: *Audio and voice* | **Status**: `RELATED`

```text
successive audio chunks → incremental hypotheses → stable committed text
```

- **English Description**: Whisper-Streaming adds a streaming policy to Whisper-like models. It is useful literature for an alternative to recording a complete utterance. Measure partial-result delay, final-result delay and endpoint behavior separately.
- **คำอธิบายภาษาไทย**: Whisper-Streaming เพิ่มนโยบายประมวลผลเสียงต่อเนื่องให้โมเดลตระกูล Whisper ใช้เป็นงานที่เกี่ยวข้องสำหรับพัฒนาระบบในอนาคต ต้องวัดเวลาข้อความชั่วคราว ข้อความสุดท้าย และการตัดจบประโยคแยกกัน
- **Units & Variables**: Latency: s; audio: timestamped samples
- **Engineering Caveat / ข้อควรระวัง**: A listen–answer loop, streaming ASR and full-duplex conversation are different capabilities; none is proved by importing faster-whisper.
- **Implementation Code Location**:
  * `apps/voice/index.html` (Line 221): *talk() — current complete-recording baseline*
- **Supporting References**:
  * `[98]` D. Macháček, R. Dabre and O. Bojar (2023) — *Turning Whisper into Real-Time Transcription System* ([Link](https://aclanthology.org/2023.ijcnlp-demo.3/))
  * `[32]` A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey and I. Sutskever (2022) — *Robust Speech Recognition via Large-Scale Weak Supervision* ([Link](https://arxiv.org/abs/2212.04356))
  * `[47]` W3C (n.d.) — *Media Capture and Streams* ([Link](https://www.w3.org/TR/mediacapture-streams/))
  * `[48]` W3C (n.d.) — *MediaStream Recording* ([Link](https://www.w3.org/TR/mediastream-recording/))

---

### Card: Hub password derivation (การแปลงรหัสผ่านของ Hub)
- **ID**: `hub-password` | **Group**: *Hub and communication* | **Status**: `IMPLEMENTED`

```text
derived_key = PBKDF2-HMAC-SHA256(password, random_salt, iterations)
current hub: 16-byte salt; 240000 iterations; compare with hmac.compare_digest
```

- **English Description**: The Python hub stores a salted derived key. These are observed settings, not a universal recommended cost. The module firmware password store has different behavior; cite the component explicitly.
- **คำอธิบายภาษาไทย**: Hub ภาษา Python เก็บค่าที่ได้จากรหัสผ่านและ salt แบบสุ่ม ค่ารอบเป็นการตั้งค่าในโค้ด ไม่ใช่คำแนะนำสากล และต่างจากวิธีเก็บรหัสผ่านในเฟิร์มแวร์โมดูล
- **Units & Variables**: Salt: bytes; iteration count: integer
- **Engineering Caveat / ข้อควรระวัง**: This documents an algorithm; it is not a complete authentication security assessment.
- **Implementation Code Location**:
  * `main_python/hub_auth.py` (Line 369): *Auth password hash*
  * `main_python/hub_auth.py` (Line 526): *Password comparison*
- **Supporting References**:
  * `[26]` K. Moriarty, B. Kaliski and A. Rusch (2017) — *PKCS #5: Password-Based Cryptography Specification Version 2.1* ([Link](https://www.rfc-editor.org/rfc/rfc8018.html))

---

### Card: Calibration slope, intercept and residuals (การฟิตสมการสอบเทียบและตรวจเศษเหลือ)
- **ID**: `calibration-fit` | **Group**: *Software tests and validation* | **Status**: `EVALUATION`

```text
y_i = a x_i + b + ε_i
a = Σ(x_i-x̄)(y_i-ȳ) / Σ(x_i-x̄)²; b = ȳ-a x̄
r_i = y_i-(a x_i+b); residual standard error = sqrt(Σr_i²/(n-2))
```

- **English Description**: For a proposed servo-angle or lift-distance experiment, fit a scale and offset against an independent instrument. Use repeated points in both directions to expose backlash; inspect residuals before trusting a straight line.
- **คำอธิบายภาษาไทย**: สำหรับการทดลองสอบเทียบมุมเซอร์โวหรือระยะยก ให้ฟิตอัตราส่วนและออฟเซ็ตเทียบเครื่องมืออิสระ วัดซ้ำทั้งสองทิศเพื่อตรวจระยะฟรี และตรวจเศษเหลือก่อนสรุปว่าเป็นเส้นตรง
- **Units & Variables**: x,y: declared physical units; slope: y-unit/x-unit; n>2
- **Engineering Caveat / ข้อควรระวัง**: Ordinary least squares treats x errors as negligible. Significant error in both axes requires a different fitted model; do not confuse residual scatter with total instrument uncertainty.
- **Implementation Code Location**:
  * `scient_test/tests/T1_nong_module.md` (Line 23): *Nong calibration experiment context*
  * `scient_test/tests/T2_lift_module.md` (Line 1): *Lift calibration experiment context*
- **Supporting References**:
  * `[104]` NIST/SEMATECH (n.d.) — *e-Handbook of Statistical Methods: Linear Least Squares Regression* ([Link](https://www.itl.nist.gov/div898/handbook/pmd/section1/pmd141.htm))
  * `[62]` JCGM (2008) — *Evaluation of measurement data — Guide to the expression of uncertainty in measurement* ([Link](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf))
  * `[125]` K. Nontapot and C. Nutsathaporn (2023) — *Uncertainty reduction of CO2 laser calibration system in National Institute of Metrology (Thailand)* ([Link](https://doi.org/10.1117/12.2671699))

---

### Card: Biometric study design and demographic reporting (การออกแบบการทดลองและรายงานผลรู้จำใบหน้า)
- **ID**: `face-study-design` | **Group**: *Camera and face recognition* | **Status**: `EVALUATION`

```text
verification: one claimed identity comparison
identification: search a gallery, with enrolled and unknown probes
report FMR/FNMR or identification metrics at a declared threshold
```

- **English Description**: Separate enrolment, threshold tuning and held-out testing by person/session as appropriate. Report image quality, lighting, distance, gallery size, unknown people and failure-to-acquire cases. Report per-group denominators and uncertainty where the sample supports it.
- **คำอธิบายภาษาไทย**: แยกข้อมูลลงทะเบียน ปรับเกณฑ์ และทดสอบที่ไม่เคยใช้ปรับระบบ ระบุแสง ระยะ ขนาดฐานข้อมูล คนที่ไม่อยู่ในฐาน และกรณีจับภาพไม่ได้ การรายงานแยกกลุ่มต้องมีจำนวนตัวอย่างและความไม่แน่นอนประกอบ
- **Units & Variables**: Rates: fractions or %; gallery size: identities
- **Engineering Caveat / ข้อควรระวัง**: A small convenience sample does not establish population-wide performance or fairness. Catalogue access does not establish compliance with every ISO test clause.
- **Implementation Code Location**:
  * `apps/faces/service.py` (Line 1): *External face-system adapter; recognition backend must be identified*
- **Supporting References**:
  * `[100]` ISO/IEC (2021) — *ISO/IEC 19795-1:2021 — Information technology — Biometric performance testing and reporting — Part 1: Principles and framework* ([Link](https://www.iso.org/standard/73515.html))
  * `[99]` P. Grother, M. Ngan and K. Hanaoka (2019) — *Face Recognition Vendor Test Part 3: Demographic Effects* ([Link](https://www.nist.gov/publications/face-recognition-vendor-test-part-3-demographic-effects))
  * `[64]` NIST/SEMATECH (n.d.) — *e-Handbook of Statistical Methods: Confidence Intervals for a Binomial Proportion* ([Link](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm))

---

### Card: Friction and backlash identification (การระบุแรงเสียดทานและระยะฟรี)
- **ID**: `friction-background` | **Group**: *Embedded hardware* | **Status**: `RELATED`

```text
For nonzero velocity: τ_f ≈ τ_c sign(ω) + bω
Model coefficients require identification; zero-speed stiction needs separate treatment
```

- **English Description**: Coulomb plus viscous friction is a simple modelling choice. The friction survey describes a broader set of phenomena, including velocity dependence and pre-sliding effects. Backlash is a separate transmission nonlinearity.
- **คำอธิบายภาษาไทย**: แรงเสียดทานคูลอมบ์ร่วมกับความหนืดเป็นแบบจำลองอย่างง่าย ต้องหาค่าสัมประสิทธิ์จากการทดลอง แรงเสียดทานขณะหยุดและระยะฟรีของเกียร์ต้องพิจารณาแยกกัน
- **Units & Variables**: τ_f,τ_c: N·m; b: N·m·s/rad; ω: rad/s
- **Engineering Caveat / ข้อควรระวัง**: The existing unsigned SigNum helper is not a correct mathematical sign for this equation; this friction compensation is not implemented.
- **Implementation Code Location**:
  * `scient_test/tests/T1_nong_module.md` (Line 23): *Proposed bidirectional motion experiment context*
- **Supporting References**:
  * `[92]` B. Armstrong-Hélouvry, P. Dupont, and C. Canudas de Wit (1994) — *A survey of models, analysis tools and compensation methods for the control of machines with friction* ([Link](https://doi.org/10.1016/0005-1098(94)90209-7))
  * `[86]` Q. Du, G. Yang, W. Wang, C.-Y. Chen and Z. Fang (2025) — *Modeling and Analysis of Transmission Efficiency for 3K Planetary Gearbox with Flexure-Based Carrier for Backdrivable Robot Joints* ([Link](https://www.mdpi.com/2076-0825/14/4/173))

---

## 5. BibTeX Quick Reference
To use these citations in LaTeX or Overleaf, download the accompanying `thesis_references.bib` file.
