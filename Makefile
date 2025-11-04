YAML=environment.yml
YAML_TMP=$(YAML:.yml=-tmp.yml) 
ENVNAME?=icecap


all:
	@rm -f TMP.yml $(YAML_TMP)
	@echo "Standard config"
	@echo $(ENVNAME) $(YAML_TMP)
	@conda remove --name $(ENVNAME) --all || true
	@conda config --set channel_priority flexible
	@sed "s#icecap#$(ENVNAME)#g" $(YAML) > $(YAML_TMP)
	conda env create -f $(YAML_TMP)
	@rm -f $(YAML_TMP)

no-ecflow:
	@echo "no ecflow"	
	rm -f TMP.yml $(YAML_TMP)
	@sed "s#icecap#$(ENVNAME)#g" $(YAML) > $(YAML_TMP)
	@sed -n '/ecflow/!p' TMP.yml > $(YAML_TMP)
	conda env create -f $(YAML_TMP)
	@rm -f $(YAML_TMP)

clean:
	@echo "Clean"
	rm -f $(YAML_TMP)
	@conda remove --name $(ENVNAME) --all
