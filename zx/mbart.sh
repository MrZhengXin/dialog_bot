# build sentencepiece
sudo apt-get install cmake build-essential pkg-config libgoogle-perftools-dev
git clone https://github.com/google/sentencepiece.git
cd /path/to/sentencepiece
mkdir build
cd build
cmake ..
make -j $(nproc)
sudo make install  # withou sudo it's cmake -D CMAKE_INSTALL_PREFIX:PATH=. && make install
sudo ldconfig -v

git clone https://github.com/pytorch/fairseq.git
cd fairseq
pip install --editable .


# download the model
wget https://dl.fbaipublicfiles.com/fairseq/models/mbart/mbart.CC25.tar.gz
tar -xzvf mbart.CC25.tar.gz

# preprocess
export SPM=/path/to/sentencepiece/build/src/spm_encode
export MODEL=/path/to/mbart.cc25/sentence.bpe.model
export SPM=sentencepiece/build/src/spm_encode
export MODEL='/path/to/mbart.cc25/sentence.bpe.model'
export SRC='src'
export TGT='tgt'
export TRAIN='train_with_knowledge'
export VALID='valid_with_knowledge'
export TEST='test_with_knowledge'
export DATA=/path/to/data
export DEST=/path/to/dest
${SPM} --model=${MODEL} < ${DATA}/${TRAIN}.${SRC} > ${DATA}/${TRAIN}.spm.${SRC} &
${SPM} --model=${MODEL} < ${DATA}/${TRAIN}.${TGT} > ${DATA}/${TRAIN}.spm.${TGT} &
${SPM} --model=${MODEL} < ${DATA}/${VALID}.${SRC} > ${DATA}/${VALID}.spm.${SRC} &
${SPM} --model=${MODEL} < ${DATA}/${VALID}.${TGT} > ${DATA}/${VALID}.spm.${TGT} &
${SPM} --model=${MODEL} < ${DATA}/${TEST}.${SRC} > ${DATA}/${TEST}.spm.${SRC} &
${SPM} --model=${MODEL} < ${DATA}/${TEST}.${TGT} > ${DATA}/${TEST}.spm.${TGT} &
DICT=/path/to/mbart.cc25/dict.txt
python preprocess.py \
--source-lang ${SRC} \
--target-lang ${TGT} \
--trainpref ${DATA}/${TRAIN}.spm \
--validpref ${DATA}/${VALID}.spm \
--testpref ${DATA}/${TEST}.spm  \
--destdir ${DEST}/${NAME} \
--thresholdtgt 0 \
--thresholdsrc 0 \
--srcdict ${DICT} \
--tgtdict ${DICT} \
--workers 70

# training

export PRETRAIN=/path/to/model/mbart.cc25
export langs=ar_AR,cs_CZ,de_DE,en_XX,es_XX,et_EE,fi_FI,fr_XX,gu_IN,hi_IN,it_IT,ja_XX,kk_KZ,ko_KR,lt_LT,lv_LV,my_MM,ne_NP,nl_XX,ro_RO,ru_RU,si_LK,tr_TR,vi_VN,zh_CN
python train.py $DEST  --encoder-normalize-before --decoder-normalize-before  --arch mbart_large --task translation_from_pretrained_bart  --source-lang src --target-lang tgt --criterion label_smoothed_cross_entropy --label-smoothing 0.2  --dataset-impl mmap --optimizer adam --adam-eps 1e-06 --adam-betas '(0.9, 0.98)' --lr-scheduler polynomial_decay --lr 3e-05 --min-lr -1 --warmup-updates 2500 --total-num-update 40000 --dropout 0.3 --attention-dropout 0.1  --weight-decay 0.0 --max-sentences 8 --update-freq 2 --save-interval 1 --save-interval-updates 5000 --keep-interval-updates 10 --no-epoch-checkpoints --seed 222 --log-format simple --log-interval 2 --reset-optimizer --reset-meters --reset-dataloader --reset-lr-scheduler --restore-file $PRETRAIN --langs $langs --layernorm-embedding  --ddp-backend no_c10d

# generation
export model=checkpoints/checkpoint_best.pt
export langs=ar_AR,cs_CZ,de_DE,en_XX,es_XX,et_EE,fi_FI,fr_XX,gu_IN,hi_IN,it_IT,ja_XX,kk_KZ,ko_KR,lt_LT,lv_LV,my_MM,ne_NP,nl_XX,ro_RO,ru_RU,si_LK,tr_TR,vi_VN,zh_CN
python generate.py $DATA  --path $model  --task translation_from_pretrained_bart --gen-subset test -t tgt -s src --bpe 'sentencepiece' --sentencepiece-vocab mbart.cc25/sentence.bpe.model   --remove-bpe 'sentencepiece' --max-sentences 32 --langs $langs > test_result.txt

cat test_result.txt | grep -P "^H" |sort -V |cut -f 3- | sed 's/\[tgt\]//g'  > test_tgt.txt
